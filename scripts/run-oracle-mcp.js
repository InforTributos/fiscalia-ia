const path = require("path");
const fs = require("fs");

const envPath = path.resolve(__dirname, "..", ".env");
if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, "utf-8").split("\n");
  for (const line of lines) {
    const m = line.match(/^\s*ORACLE_(\w+)\s*=\s*(.+)\s*$/);
    if (m) {
      process.env[`ORACLE_${m[1]}`] = m[2].replace(/["']/g, "").trim();
    }
  }
}

if (!process.env.ORACLE_USER) {
  throw new Error("Falta ORACLE_USER en .env");
}
if (!process.env.ORACLE_PASSWORD) {
  throw new Error("Falta ORACLE_PASSWORD en .env");
}
if (!process.env.ORACLE_CONNECTION_STRING) {
  const host = process.env.ORACLE_HOST || "localhost";
  const port = process.env.ORACLE_PORT || "1521";
  const service = process.env.ORACLE_SERVICE || "ORCL";
  process.env.ORACLE_CONNECTION_STRING = `${host}:${port}/${service}`;
}
process.env.ORACLE_MODE = process.env.ORACLE_MODE || "readonly";
process.env.ORACLE_MAX_ROWS = process.env.ORACLE_MAX_ROWS || "500";

console.error(
  `[oracle-mcp] Conectando a ${process.env.ORACLE_USER}@${process.env.ORACLE_CONNECTION_STRING} (${process.env.ORACLE_MODE})`
);

require("mcp-oracle-db");
