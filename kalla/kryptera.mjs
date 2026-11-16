// Krypterar bokens texter och ljud så att de kan ligga öppet på GitHub Pages.
// Anropas av bygg_texter.py:  node kryptera.mjs <salt-base64> <in-fil> <ut-fil> [<in-fil> <ut-fil> ...]
// Användarnamn och lösenord kommer i miljövariablerna TEXTER_ANV och TEXTER_LOSEN.
//
// Nyckeln: PBKDF2-SHA256 (600 000 varv) av "användarnamn\nlösenord". Varje fil: iv (12 byte) + AES-GCM.
// iv tas från innehållets SHA-256, så en oförändrad fil blir byte för byte likadan vid nästa bygge.
import { readFileSync, writeFileSync } from "node:fs";

const [salt64, ...par] = process.argv.slice(2);
const anv = (process.env.TEXTER_ANV || "").trim().toLowerCase();
const losen = process.env.TEXTER_LOSEN || "";
if (!anv || !losen || par.length % 2) {
  console.error("Användning: TEXTER_ANV=… TEXTER_LOSEN=… node kryptera.mjs salt in ut [in ut …]");
  process.exit(1);
}
const { subtle } = globalThis.crypto;
const bas = await subtle.importKey("raw", new TextEncoder().encode(anv + "\n" + losen), "PBKDF2", false, ["deriveKey"]);
const nyckel = await subtle.deriveKey(
  { name: "PBKDF2", salt: Buffer.from(salt64, "base64"), iterations: 600000, hash: "SHA-256" },
  bas, { name: "AES-GCM", length: 256 }, false, ["encrypt"]);

for (let k = 0; k < par.length; k += 2) {
  const data = readFileSync(par[k]);
  const iv = new Uint8Array(await subtle.digest("SHA-256", data)).slice(0, 12);
  const ct = new Uint8Array(await subtle.encrypt({ name: "AES-GCM", iv }, nyckel, data));
  writeFileSync(par[k + 1], Buffer.concat([iv, ct]));
}
console.log(`${par.length / 2} filer krypterade`);
