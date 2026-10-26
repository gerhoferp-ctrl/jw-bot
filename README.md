# Bot Telegram – Novità JW.ORG

Ti manda un messaggio Telegram per ogni nuovo elemento pubblicato su
https://www.jw.org/it/cosa-nuovo/ (articoli, news, canzoni, riviste, guide…).
Gira gratis su GitHub e controlla la pagina ogni 30 minuti.

## Attivazione (5 minuti, dal telefono)

1. **Crea il bot su Telegram**
   - Cerca **@BotFather** e scrivigli `/newbot`.
   - Scegli un nome (es. `Novità JW`) e un nome utente che finisca in `bot` (es. `novita_jw_peter_bot`).
   - BotFather ti risponde con un **token** tipo `123456789:AAH...`. Copialo.

2. **Avvia il tuo bot**: apri il link che ti ha dato BotFather (t.me/…) e premi **Avvia**.

3. **Inserisci il token su GitHub**
   In questo repository: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `TELEGRAM_TOKEN`
   - Secret: il token copiato al punto 1

4. **Avvia il bot**: **Actions → Bot novità JW.ORG → Run workflow**.
   Dopo un minuto ricevi su Telegram un messaggio di conferma con l'ultima uscita.
   Da lì in poi ricevi un messaggio per ogni novità.

## Note
- Per cambiare la frequenza modifica la riga `cron` in `.github/workflows/jw-bot.yml` (es. `0 * * * *` = ogni ora).
- Se smetti di ricevere messaggi, controlla in **Actions** l'esito dell'ultima esecuzione.
