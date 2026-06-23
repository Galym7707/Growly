"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/icons";
import { Status } from "@/components/ui";
import { useLanguage } from "@/lib/i18n";

export type ChannelDescriptor = {
  slug: string;
  label: string;
  connected: boolean;
  accountLabel: string;
};

export function ChannelSelector({
  channels,
  selected,
  onToggle,
}: {
  channels: ChannelDescriptor[];
  selected: string[];
  onToggle: (slug: string) => void;
}) {
  const { t } = useLanguage();
  const [showDisconnected, setShowDisconnected] = useState(false);
  const connected = channels.filter((channel) => channel.connected);
  const disconnected = channels.filter((channel) => !channel.connected);

  return (
    <div className="channel-selector">
      <h3 className="publish-subhead">{t("Куда публикуем")}</h3>

      {connected.length ? (
        <div className="channel-list">
          {connected.map((channel) => (
            <label className="channel-row" key={channel.slug}>
              <input
                checked={selected.includes(channel.slug)}
                onChange={() => onToggle(channel.slug)}
                type="checkbox"
              />
              <span className="channel-name">{channel.label}</span>
              <span className="channel-account muted">{channel.accountLabel}</span>
              <Status value="active">{t("Подключено")}</Status>
            </label>
          ))}
        </div>
      ) : (
        <p className="draft-helper">
          {t("Автопубликация не подключена. Growly может подготовить пакет для ручной публикации.")}
        </p>
      )}

      {disconnected.length ? (
        <div className="channel-disconnected">
          <button
            aria-expanded={showDisconnected}
            className="channel-disclosure"
            onClick={() => setShowDisconnected((value) => !value)}
            type="button"
          >
            <Icon name="chevron" className={showDisconnected ? "is-open" : ""} />
            {t("Недоступные каналы ({count})", { count: disconnected.length })}
          </button>
          {showDisconnected ? (
            <div className="channel-list channel-list-muted">
              {disconnected.map((channel) => (
                <label className="channel-row is-disabled" key={channel.slug}>
                  <input checked={false} disabled type="checkbox" />
                  <span className="channel-name">{channel.label}</span>
                  <Status value="disabled">{t("Не подключено")}</Status>
                </label>
              ))}
              <Link className="button button-secondary button-small button-wide" href="/integrations">
                <Icon name="settings" />
                {t("Настроить интеграции")}
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
