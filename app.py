import os
import hashlib
import discord
from discord.ext import commands
from dotenv import load_dotenv
import time
import json
from discord import app_commands

load_dotenv('.env')
token = os.getenv("TOKEN")
ADMIN_USERS = os.getenv("ADMIN_USERS")
WALLET_FILE = "wallets.json"
ROLE = {
    "NormalUser": 50,
    "VIP": 500,
    "SuperUser": 1000
}


class Block:
    # blockの構成
    # index	ブロック番号（高さ）
    # timestamp	ブロックの生成時間
    # transactions	このブロックに含まれる取引
    # prev_hash	1つ前のブロックのハッシュ
    # nonce	発言メッセージ（ナンス値）
    # hash	このブロックのSHA256ハッシュ値

    def __init__(self, index, timestamp, transactions, prev_hash, nonce, hash):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.hash = hash

    # jsonに変換
    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }
    
class Blockchain:
    # Blockでできたchainを構成
    def __init__(self):
        self.chain = []
        self.pending_tx = []
        self.load_chain()

    # 一番最初のブロック生成
    def create_genesis(self):
        genesis = Block(0, time.time(), ["Genesis Block"], "0", "0", self.hash_block("0", "0", ["Genesis Block"]))
        self.chain.append(genesis)
        self.save_chain()

    # 最新ブロックを返す
    def return_latest_block(self):
        return self.chain[-1]

    # 前のハッシュ、ナンス値、トランザクションをハッシュ
    def hash_block(self, prev_hash, nonce, transactions):
        block_string = json.dumps({
            "prev_hash": prev_hash,
            "nonce": nonce,
            "transactions": transactions
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    # mining
    def mining(self, nonce):
        last = self.return_latest_block()
        tx = [f"user mined using nonce "]
        hash = self.hash_block(last.hash, nonce, tx)
        if hash.startswith("000"):
            block = Block(len(self.chain), time.time(), tx, last.hash, nonce, hash)
            self.chain.append(block)
            self.save_chain()
            return 3, block
        elif hash.startswith("00"):
            block = Block(len(self.chain), time.time(), tx, last.hash, nonce, hash)
            self.chain.append(block)
            self.save_chain()
            return 2, block
        elif hash.startswith("0"):
            block = Block(len(self.chain), time.time(), tx, last.hash, nonce, hash)
            self.chain.append(block)
            self.save_chain()
            return 1, block
        return False, hash

    def save_chain(self):
        with open("chain.json", "w") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def load_chain(self):
        if not os.path.exists("chain.json"):
            self.create_genesis()
        else:
            with open("chain.json", "r") as f:
                data = json.load(f)
                self.chain = [Block(**b) for b in data]

def load_wallets():
    try:
        with open(WALLET_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_wallets(wallets):
    with open(WALLET_FILE, "w") as f:
        json.dump(wallets, f)

def add_tokens(user_id, amount):
    wallets = load_wallets()
    wallets[user_id] = wallets.get(user_id, 0) + amount
    save_wallets(wallets)

def get_balance(user_id):
    return load_wallets().get(user_id, 0)

def spend_tokens(user_id, amount):
    wallets = load_wallets()
    if wallets.get(user_id, 0) >= amount:
        wallets[user_id] -= amount
        save_wallets(wallets)
        return True
    return False


blockchain = Blockchain()

intents = discord.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    case_insensitive=True,
    intents=intents
)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready: {bot.user}")


# 特定キーワードでポイント付与
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    nonce = message.content.strip()
    user = message.author.id
    success, result = blockchain.mining(nonce)

    if success == 3:
        add_tokens(user, 100)
        await message.channel.send(f"{message.author.mention} さん、貴方はウルトラレア！")
    elif success == 2:
        add_tokens(user, 10)
        await message.channel.send(f"{message.author.mention} さん、貴方はスーパーレア！")
    elif success == 1:
        add_tokens(user, 1)
        await message.channel.send(f"{message.author.mention} さん、貴方はレア！")

    await bot.process_commands(message)

# コマンドでポイント確認
@bot.tree.command(name="balance")
async def balance(interaction:discord.Interaction):# ctxにはコマンドの実行に関する情報を持っている(打った人など)
    user_id = str(interaction.user.id)
    balance = get_balance(user_id)
    await interaction.response.send_message(
        f"{interaction.user.display_name} さんの残高は {balance} DISCOIN です。",
        ephemeral=True
    )
    
@bot.tree.command(name="buy_role", description="ロールを購入します")
@app_commands.describe(role_name="購入したいロールの名前")
async def buy_role(interaction: discord.Interaction, role_name: str):
    if interaction.user.bot:
        return
    
    user_id = str(interaction.user.id)
    role_price = ROLE.get(role_name)
    
    if role_price is None:
        await interaction.response.send_message(f"`{role_name}` は購入できるロールではありません。", ephemeral=True)
        return

    if not spend_tokens(user_id, role_price):
        await interaction.response.send_message("残高が足りません。", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if role:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"{role_name} ロールを購入しました！", ephemeral=True)
    else:
        await interaction.response.send_message("指定されたロールが見つかりません。", ephemeral=True)


@bot.tree.command(name="airdrop", description="指定したユーザーにDISCOINを配布")
@app_commands.describe(member="配布先", amount="配布金額")
async def airdrop(interaction: discord.Interaction, member: discord.Member, amount: int):
    if str(interaction.user.id) not in ADMIN_USERS:
        await interaction.response.send_message("あなたにはこの操作を行う権限がありません。", ephemeral=True)
        return

    add_tokens(str(member.id), amount)
    await interaction.response.send_message(f"{member.display_name} に {amount} DISCOIN を配布しました。")


bot.run(token)