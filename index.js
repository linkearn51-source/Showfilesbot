require("dotenv").config();
const { Telegraf, Markup } = require("telegraf");
const { v4: uuidv4 } = require("uuid");
const { Pool } = require("pg");

const bot = new Telegraf(process.env.BOT_TOKEN);

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

const STORAGE_CHANNEL = process.env.STORAGE_CHANNEL_ID;
const FORCE_CHANNEL = process.env.FORCE_CHANNEL;
const ADMIN_ID = Number(process.env.ADMIN_ID);

const uploads = {};
const PAGE_SIZE = 5;
let broadcastMode = false;

/* ================= DATABASE ================= */

(async () => {

  await pool.query(`
  CREATE TABLE IF NOT EXISTS files(
  id SERIAL PRIMARY KEY,
  user_id BIGINT,
  code TEXT,
  messages TEXT,
  total_files INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )`);

  await pool.query(`
  CREATE TABLE IF NOT EXISTS users(
  id BIGINT PRIMARY KEY
  )`);

})();

/* ================= SAVE USER ================= */

async function saveUser(id){

  await pool.query(
    "INSERT INTO users(id) VALUES($1) ON CONFLICT DO NOTHING",
    [id]
  );

}

/* ================= FORCE JOIN ================= */

async function isJoined(ctx){

  try{

    const member = await ctx.telegram.getChatMember(
      FORCE_CHANNEL,
      ctx.from.id
    );

    return ["member","administrator","creator"].includes(member.status);

  }catch{

    return false;

  }

}

/* ================= SEND FILE ================= */

async function sendFiles(ctx,data){

  const msgs = JSON.parse(data.messages);

  for(const msg of msgs){

    await ctx.telegram.copyMessage(
      ctx.chat.id,
      STORAGE_CHANNEL,
      msg
    );

  }

}

/* ================= START ================= */

bot.start(async(ctx)=>{

  await saveUser(ctx.from.id);

  const code = ctx.startPayload;

  if(code){

    const q = await pool.query(
      "SELECT * FROM files WHERE code=$1",
      [code]
    );

    if(!q.rows.length)
      return ctx.reply("❌ Code tidak ditemukan");

    await sendFiles(ctx,q.rows[0]);
    return;

  }

  const joined = await isJoined(ctx);

  if(!joined){

    return ctx.reply(
      "⚠️ Wajib join channel dulu",
      Markup.inlineKeyboard([
        Markup.button.url(
          "JOIN CHANNEL",
          `https://t.me/${FORCE_CHANNEL.replace("@","")}`
        )
      ])
    );

  }

  ctx.reply(
    "📦 STORAGE BOT MENU",
    Markup.keyboard([
      ["📤 Upload","📁 My Files"],
      ["📊 Statistik","ℹ️ Bantuan"]
    ]).resize()
  );

});

/* ================= UPLOAD ================= */

bot.hears("📤 Upload",(ctx)=>{

  uploads[ctx.from.id] = { messages:[] };

  ctx.reply("Kirim semua video/file lalu tekan CREATE.");

});

/* ================= RECEIVE FILE ================= */

bot.on(["video","document"],async(ctx)=>{

  if(!uploads[ctx.from.id]) return;

  const forward = await ctx.forwardMessage(
    STORAGE_CHANNEL,
    ctx.chat.id,
    ctx.message.message_id
  );

  uploads[ctx.from.id].messages.push(forward.message_id);

  const total = uploads[ctx.from.id].messages.length;

  ctx.reply(
    `✅ File diterima\n📁 Total : ${total}`,
    Markup.inlineKeyboard([
      Markup.button.callback("CREATE","create_files")
    ])
  );

});

/* ================= CREATE ================= */

bot.action("create_files",async(ctx)=>{

  const data = uploads[ctx.from.id];

  if(!data || !data.messages.length)
    return ctx.answerCbQuery("Belum ada file");

  const code = uuidv4().slice(0,8);

  await pool.query(
    "INSERT INTO files(user_id,code,messages,total_files) VALUES($1,$2,$3,$4)",
    [
      ctx.from.id,
      code,
      JSON.stringify(data.messages),
      data.messages.length
    ]
  );

  delete uploads[ctx.from.id];

  const botInfo = await bot.telegram.getMe();

  ctx.reply(
`✅ FILE CREATED

CODE
${code}

LINK
https://t.me/${botInfo.username}?start=${code}`
  );

});

/* ================= MY FILES ================= */

bot.hears("📁 My Files",(ctx)=>{

  sendMyFiles(ctx,0);

});

async function sendMyFiles(ctx,page){

  const userId = ctx.from.id;
  const offset = page * PAGE_SIZE;

  const q = await pool.query(
    "SELECT * FROM files WHERE user_id=$1 ORDER BY id DESC LIMIT $2 OFFSET $3",
    [userId,PAGE_SIZE,offset]
  );

  if(!q.rows.length)
    return ctx.reply("Tidak ada file.");

  let text = "📁 MY FILES\n\n";

  q.rows.forEach(f=>{
    text += `🔑 ${f.code} | 📦 ${f.total_files} file\n`;
  });

  const buttons = [];

  if(page>0)
    buttons.push(Markup.button.callback("⬅️ PREV",`page_${page-1}`));

  if(q.rows.length===PAGE_SIZE)
    buttons.push(Markup.button.callback("NEXT ➡️",`page_${page+1}`));

  ctx.reply(text,Markup.inlineKeyboard(buttons));

}

bot.action(/page_(.+)/,async(ctx)=>{

  const page = parseInt(ctx.match[1]);
  await ctx.deleteMessage();
  sendMyFiles(ctx,page);

});

/* ================= STATISTIK ================= */

bot.hears("📊 Statistik",async(ctx)=>{

  const users = await pool.query("SELECT COUNT(*) FROM users");
  const files = await pool.query("SELECT COUNT(*) FROM files");

  ctx.reply(
`📊 STATISTIK BOT

👤 Users : ${users.rows[0].count}
📁 Files : ${files.rows[0].count}`
  );

});

/* ================= BROADCAST ================= */

bot.command("broadcast",(ctx)=>{

  if(ctx.from.id !== ADMIN_ID)
    return ctx.reply("❌ Hanya admin");

  broadcastMode = true;

  ctx.reply("Kirim pesan untuk broadcast");

});

bot.on("text",async(ctx)=>{

  if(broadcastMode && ctx.from.id===ADMIN_ID){

    broadcastMode = false;

    const users = await pool.query("SELECT id FROM users");

    for(const u of users.rows){

      try{

        await ctx.telegram.sendMessage(u.id,ctx.message.text);

      }catch{}

    }

    return ctx.reply("✅ Broadcast selesai");

  }

  const code = ctx.message.text.trim();

  if(code.length<6) return;

  const q = await pool.query(
    "SELECT * FROM files WHERE code=$1",
    [code]
  );

  if(!q.rows.length) return;

  await sendFiles(ctx,q.rows[0]);

});

/* ================= HELP ================= */

bot.hears("ℹ️ Bantuan",(ctx)=>{

  ctx.reply(
`📖 CARA PAKAI

1. Klik Upload
2. Kirim video/file
3. Tekan CREATE
4. Bot memberi CODE + LINK

User bisa ambil file dengan:
- klik link bot
- kirim CODE ke bot`
  );

});

bot.launch();

console.log("BOT RUNNING");
