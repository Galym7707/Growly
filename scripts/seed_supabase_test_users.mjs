import { createClient } from "@supabase/supabase-js";
import fs from "node:fs";
import path from "node:path";

const rootDir = process.cwd();
const env = readEnv(path.join(rootDir, ".env"));

const supabaseUrl = env.SUPABASE_URL || env.NEXT_PUBLIC_SUPABASE_URL;
const serviceKey = env.SUPABASE_SECRET_API_KEY;
const count = Number.parseInt(process.env.TEST_USER_COUNT || "100", 10);
const prefix = process.env.TEST_USER_PREFIX || "growly-test-user";
const domain = process.env.TEST_USER_DOMAIN || "example.test";
const password = process.env.TEST_USER_PASSWORD || makePassword();

if (!supabaseUrl || !serviceKey) {
  throw new Error("Missing SUPABASE_URL or SUPABASE_SECRET_API_KEY in .env.");
}
if (!Number.isInteger(count) || count < 1 || count > 1000) {
  throw new Error("TEST_USER_COUNT must be an integer from 1 to 1000.");
}

const supabase = createClient(supabaseUrl, serviceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

const created = [];
const existing = [];
const failed = [];

for (let index = 1; index <= count; index += 1) {
  const email = `${prefix}-${String(index).padStart(3, "0")}@${domain}`;
  const { data, error } = await supabase.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    user_metadata: {
      source: "codex-test-seed",
      test_user: true,
      batch: prefix,
    },
  });

  if (!error) {
    created.push({ email, id: data.user?.id || null });
    console.log(`created ${email}`);
    continue;
  }

  if (isAlreadyExistsError(error)) {
    existing.push(email);
    console.log(`exists  ${email}`);
    continue;
  }

  failed.push({ email, message: error.message });
  console.error(`failed  ${email}: ${error.message}`);
}

const outputDir = path.join(rootDir, "logs");
fs.mkdirSync(outputDir, { recursive: true });
const outputPath = path.join(outputDir, `${prefix}-supabase-users.json`);
fs.writeFileSync(
  outputPath,
  JSON.stringify(
    {
      created_at: new Date().toISOString(),
      count_requested: count,
      password,
      created,
      existing,
      failed,
    },
    null,
    2,
  ),
);

console.log(
  JSON.stringify(
    {
      requested: count,
      created: created.length,
      existing: existing.length,
      failed: failed.length,
      output: outputPath,
    },
    null,
    2,
  ),
);

if (failed.length > 0) {
  process.exitCode = 1;
}

function readEnv(filePath) {
  if (!fs.existsSync(filePath)) return {};
  return Object.fromEntries(
    fs
      .readFileSync(filePath, "utf8")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#") && line.includes("="))
      .map((line) => {
        const separator = line.indexOf("=");
        const key = line.slice(0, separator).trim();
        const value = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
        return [key, value];
      }),
  );
}

function makePassword() {
  return `GrowlyTest-${cryptoRandom()}-${Date.now()}!`;
}

function cryptoRandom() {
  return Math.random().toString(36).slice(2, 10);
}

function isAlreadyExistsError(error) {
  return /already|exists|registered/i.test(error.message || "");
}
