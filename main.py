from __future__ import annotations

import html
import io
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


# =============================================================================
# 1. SOZLAMALAR
# =============================================================================
class Sozlamalar:
    """Ilovaning umumiy o'zgarmas sozlamalari."""

    SAHIFA_NOMI: str = "Universal Analitika Paneli"
    IKONKA: str = "📊"
    RANG_ASOSIY: str = "#6C63FF"
    PALITRA: list[str] = [
        "#6C63FF", "#00C2A8", "#FF6584", "#FFB020", "#3B82F6",
        "#A855F7", "#22C55E", "#F97316", "#EC4899", "#14B8A6",
    ]
    GRADIENTLAR: list[str] = [
        "linear-gradient(135deg,#6C63FF,#8E7CFF)",
        "linear-gradient(135deg,#00B39B,#2DD4BF)",
        "linear-gradient(135deg,#FF5C7C,#FF8FA3)",
        "linear-gradient(135deg,#F59E0B,#FF8A00)",
        "linear-gradient(135deg,#3B82F6,#60A5FA)",
        "linear-gradient(135deg,#A855F7,#EC4899)",
    ]
    FUNKSIYALAR: dict[str, str] = {
        "Yig'indi": "sum",
        "O'rtacha": "mean",
        "Medyana": "median",
        "Soni": "count",
        "Maksimum": "max",
        "Minimum": "min",
    }
    DAVRLAR: dict[str, str] = {
        "Kunlik": "D",
        "Haftalik": "W",
        "Oylik": "MS",
        "Choraklik": "QS",
        "Yillik": "YS",
    }
    HAFTA_KUNLARI: list[str] = [
        "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba",
    ]
    OYLAR: list[str] = [
        "Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek",
    ]
    MAX_KATEGORIYA: int = 50
    KALIT_SOZLAR: tuple[str, ...] = (
        "tushum", "sotuv", "summa", "revenue", "sales", "amount",
        "narx", "price", "jami", "total", "foyda", "profit",
    )
    QOLLANADIGAN_FORMATLAR: list[str] = [
        "csv", "tsv", "txt", "xlsx", "xlsm", "xls", "json", "parquet",
    ]


# =============================================================================
# 2. YORDAMCHI FUNKSIYALAR
# =============================================================================
def qisqa_raqam(qiymat: float | None) -> str:
    """Katta sonlarni qisqa ko'rinishga o'tkazadi (1.25 mln, 3.40 mlrd ...)."""
    if qiymat is None or pd.isna(qiymat):
        return "—"
    mutlaq = abs(float(qiymat))
    for chegara, qoshimcha in ((1e12, " trln"), (1e9, " mlrd"), (1e6, " mln"), (1e3, " ming")):
        if mutlaq >= chegara:
            return f"{qiymat / chegara:,.2f}{qoshimcha}"
    if float(qiymat).is_integer():
        return f"{int(qiymat):,}"
    return f"{qiymat:,.2f}"


def sparkline_svg(qiymatlar: pd.Series | list[float], w: int = 130, h: int = 34) -> str:
    """Kichik chiziqli grafikni (sparkline) SVG ko'rinishida qaytaradi."""
    v = np.array([q for q in qiymatlar if pd.notna(q)], dtype=float)[-40:]
    if len(v) < 2:
        return ""
    minimum, maksimum = v.min(), v.max()
    oraliq = (maksimum - minimum) or 1.0
    xs = np.linspace(2, w - 2, len(v))
    ys = h - 3 - (v - minimum) / oraliq * (h - 6)
    nuqtalar = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<polyline points="{nuqtalar}" fill="none" stroke="rgba(255,255,255,.95)" '
        f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def davr_yorligi(vaqt: pd.Timestamp, davr_nomi: str) -> str:
    """Davr turiga qarab sanani chiroyli matnga aylantiradi."""
    if davr_nomi == "Yillik":
        return vaqt.strftime("%Y")
    if davr_nomi in ("Oylik", "Choraklik"):
        return vaqt.strftime("%Y-%m")
    return vaqt.strftime("%Y-%m-%d")


def agregatsiya(df: pd.DataFrame, guruh: str | list[str], metrika: str | None, funk: str) -> pd.DataFrame:
    """Guruhlar bo'yicha agregatsiya. Natija ustuni doim 'Qiymat' deb nomlanadi."""
    g = df.groupby(guruh, observed=True, dropna=True)
    natija = g.size() if (metrika is None or funk == "count") else g[metrika].agg(funk)
    return natija.rename("Qiymat").reset_index()


def skalyar(df: pd.DataFrame, metrika: str | None, funk: str) -> float:
    """Butun jadval bo'yicha bitta agregat qiymat."""
    if df.empty:
        return 0.0
    if metrika is None or funk == "count":
        return float(len(df))
    qiymat = getattr(df[metrika], funk)()
    return 0.0 if pd.isna(qiymat) else float(qiymat)


def vaqt_qatori(df: pd.DataFrame, sana: str, metrika: str | None, funk: str, davr: str) -> pd.DataFrame:
    """Ko'rsatkichni tanlangan davr bo'yicha yig'adi (resample)."""
    d = df.dropna(subset=[sana])
    if d.empty:
        return pd.DataFrame({sana: pd.Series(dtype="datetime64[ns]"), "Qiymat": pd.Series(dtype=float)})
    d = d.set_index(sana).sort_index()
    if metrika is None or funk == "count":
        q = d.resample(davr).size()
    else:
        q = d[metrika].resample(davr).agg(funk)
    return q.rename("Qiymat").reset_index()


def sifat_bahosi(df: pd.DataFrame) -> dict[str, float]:
    """Ma'lumot sifati: yetishmovchilik, takrorlanish va umumiy ball (0-100)."""
    jami_katak = df.size or 1
    yetishmagan = float(df.isna().sum().sum() / jami_katak * 100)
    takror = float(df.duplicated().mean() * 100) if len(df) else 0.0
    ball = max(0.0, 100.0 - yetishmagan - takror * 0.5)
    return {"yetishmagan": yetishmagan, "takror": takror, "ball": ball}


def chetlashmalar_jadvali(df: pd.DataFrame, raqamli: list[str]) -> pd.DataFrame:
    """IQR usuli bo'yicha har bir raqamli ustundagi chetlashmalarni topadi."""
    qatorlar: list[dict] = []
    for ustun in raqamli:
        s = df[ustun].dropna()
        if len(s) < 8:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        quyi, yuqori = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        soni = int(((s < quyi) | (s > yuqori)).sum())
        if soni:
            qatorlar.append({
                "Ustun": ustun,
                "Chetlashmalar soni": soni,
                "Ulushi (%)": round(soni / len(s) * 100, 2),
                "Quyi chegara": round(float(quyi), 2),
                "Yuqori chegara": round(float(yuqori), 2),
            })
    if not qatorlar:
        return pd.DataFrame(columns=["Ustun", "Chetlashmalar soni", "Ulushi (%)", "Quyi chegara", "Yuqori chegara"])
    return pd.DataFrame(qatorlar).sort_values("Ulushi (%)", ascending=False).reset_index(drop=True)
@st.cache_data(show_spinner="Demo ma'lumot yaratilmoqda...")
def demo_malumot(qatorlar: int = 4000) -> pd.DataFrame:
    """Fayl yuklanmaganda ko'rsatiladigan sun'iy savdo ma'lumoti."""
    r = np.random.default_rng(42)
    sanalar = pd.to_datetime("2024-01-01") + pd.to_timedelta(r.integers(0, 730, qatorlar), unit="D")
    narx_oraliqlari = {
        "Elektronika": (300, 1500), "Kiyim": (20, 200), "Oziq-ovqat": (2, 40),
        "Uy-ro'zg'or": (15, 300), "Sport": (25, 400),
    }
    kategoriya = r.choice(list(narx_oraliqlari), qatorlar, p=[0.22, 0.25, 0.28, 0.15, 0.10])
    narx = np.array([r.uniform(*narx_oraliqlari[k]) for k in kategoriya]).round(2)
    miqdor = r.integers(1, 8, qatorlar)
    chegirma = r.choice([0, 0, 0, 5, 10, 15, 20], qatorlar)
    kunlar = (sanalar - sanalar.min()).days.values
    mavsum = 1 + 0.25 * np.sin((sanalar.month.values - 3) / 12 * 2 * np.pi) + kunlar / 730 * 0.4
    tushum = (narx * miqdor * (1 - chegirma / 100) * mavsum).round(2)
    tushum[:15] *= 8  # ataylab bir nechta chetlashma qo'shamiz
    foyda = (tushum * r.uniform(0.08, 0.35, qatorlar)).round(2)
    baho = np.clip(r.normal(4.1, 0.7, qatorlar), 1, 5).round(1)
    baho[r.random(qatorlar) < 0.04] = np.nan

    return pd.DataFrame({
        "Buyurtma_ID": np.arange(1, qatorlar + 1),
        "Sana": sanalar,
        "Viloyat": r.choice(
            ["Toshkent", "Samarqand", "Buxoro", "Andijon", "Farg'ona", "Namangan", "Xorazm", "Qashqadaryo"],
            qatorlar, p=[0.30, 0.15, 0.10, 0.12, 0.10, 0.08, 0.07, 0.08]),
        "Kategoriya": kategoriya,
        "Mijoz_turi": r.choice(["Oddiy", "Doimiy", "Korporativ"], qatorlar, p=[0.55, 0.30, 0.15]),
        "Miqdor": miqdor,
        "Narx": narx,
        "Chegirma_%": chegirma,
        "Tushum": tushum,
        "Foyda": foyda,
        "Baho": baho,
    })


@st.cache_data(show_spinner="Fayl o'qilmoqda...")
def faylni_oqish(baytlar: bytes, fayl_nomi: str, varaq: str | None = None) -> pd.DataFrame:
    """Yuklangan faylni kengaytmasiga qarab DataFrame'ga o'qiydi."""
    kengaytma = fayl_nomi.rsplit(".", 1)[-1].lower()
    oqim = lambda: io.BytesIO(baytlar)  # noqa: E731

    if kengaytma in ("csv", "tsv", "txt"):
        oxirgi_xato: Exception | None = None
        for kodlash in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
            try:
                return pd.read_csv(oqim(), sep=None, engine="python", encoding=kodlash)
            except UnicodeDecodeError as xato:
                oxirgi_xato = xato
        raise ValueError(f"Fayl kodlashini aniqlab bo'lmadi: {oxirgi_xato}")
    if kengaytma in ("xlsx", "xlsm", "xls"):
        return pd.read_excel(oqim(), sheet_name=varaq or 0)
    if kengaytma == "json":
        try:
            return pd.read_json(oqim())
        except ValueError:
            return pd.read_json(oqim(), lines=True)
    if kengaytma == "parquet":
        return pd.read_parquet(oqim())
    raise ValueError(f"Qo'llanmaydigan format: .{kengaytma}")


@st.cache_data
def excel_varaqlari(baytlar: bytes) -> list[str]:
    """Excel faylidagi varaqlar (sheet) nomlari."""
    return pd.ExcelFile(io.BytesIO(baytlar)).sheet_names


@dataclass
class Profil:
    """Ustunlarning avtomatik aniqlangan turlari."""

    raqamli: list[str]
    kategorik: list[str]
    sanali: list[str]
    matnli: list[str]
    id_ustunlar: list[str]


@st.cache_data(show_spinner="Ma'lumot tahlilga tayyorlanmoqda...")
def tayyorlash(xom: pd.DataFrame) -> tuple[pd.DataFrame, Profil]:
    """Ustunlarni tozalaydi, turini aniqlaydi (raqam / sana / kategoriya / matn / ID)."""
    df = xom.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all").reset_index(drop=True)

    # 3.1. Matn ko'rinishidagi raqam va sanalarni haqiqiy turga o'tkazish
    for ustun in df.columns:
        s = df[ustun]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_bool_dtype(s):
            continue
        toza = s.astype("string").str.strip()
        bor = toza.dropna()
        if bor.empty:
            continue
        raqam = pd.to_numeric(
            toza.str.replace(r"\s+", "", regex=True).str.replace(",", ".", regex=False), errors="coerce"
        )
        if raqam.notna().sum() / len(bor) >= 0.95:
            df[ustun] = raqam
            continue
        namuna = bor.head(200)
        if namuna.str.contains(r"[-/.:]", regex=True).mean() > 0.8:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tekshiruv = pd.to_datetime(namuna, errors="coerce")
                if tekshiruv.notna().mean() >= 0.9:
                    df[ustun] = pd.to_datetime(toza, errors="coerce")

    # 3.2. Ustunlarni rollarga ajratish
    raqamli: list[str] = []
    kategorik: list[str] = []
    sanali: list[str] = []
    matnli: list[str] = []
    id_ustunlar: list[str] = []
    for ustun in df.columns:
        s = df[ustun]
        noyob = s.nunique(dropna=True)
        if pd.api.types.is_datetime64_any_dtype(s):
            sanali.append(ustun)
        elif pd.api.types.is_bool_dtype(s):
            df[ustun] = s.astype(str)
            kategorik.append(ustun)
        elif pd.api.types.is_numeric_dtype(s):
            if pd.api.types.is_integer_dtype(s) and noyob == s.notna().sum() and noyob > 20:
                id_ustunlar.append(ustun)
            else:
                raqamli.append(ustun)
                if noyob <= 12:
                    kategorik.append(ustun)
        else:
            df[ustun] = s.astype("object").where(s.notna(), np.nan)
            if noyob <= Sozlamalar.MAX_KATEGORIYA:
                kategorik.append(ustun)
            else:
                matnli.append(ustun)
    return df, Profil(raqamli, kategorik, sanali, matnli, id_ustunlar)


# =============================================================================
# 4. YON PANEL: MANBA, SOZLAMALAR, FILTRLAR
# =============================================================================
class MalumotManbai:
    """Yon panelda fayl yuklash oynasini boshqaradi."""

    def yuklash(self) -> tuple[pd.DataFrame, str, str]:
        """(DataFrame, ko'rinadigan nom, vidjet kalitlari uchun prefiks) qaytaradi."""
        sb = st.sidebar
        sb.markdown("## 📂 Ma'lumot manbai")
        fayl = sb.file_uploader(
            "Kompyuterdan fayl tanlang",
            type=Sozlamalar.QOLLANADIGAN_FORMATLAR,
            help="CSV, Excel, JSON yoki Parquet. Ustun turlari avtomatik aniqlanadi.",
        )
        if fayl is None:
            sb.caption("💡 Fayl yuklanmaguncha demo ma'lumot (savdo) ko'rsatiladi.")
            return demo_malumot(), "Demo ma'lumot (savdo)", "demo"

        baytlar = fayl.getvalue()
        varaq: str | None = None
        if fayl.name.lower().endswith((".xlsx", ".xlsm", ".xls")):
            varaqlar = excel_varaqlari(baytlar)
            if len(varaqlar) > 1:
                varaq = sb.selectbox("📑 Varaq (sheet)", varaqlar)
        try:
            df = faylni_oqish(baytlar, fayl.name, varaq)
        except Exception as xato:  # noqa: BLE001
            st.error(f"Faylni o'qib bo'lmadi: {xato}")
            st.stop()
        return df, fayl.name, f"{fayl.name}_{len(baytlar)}_{varaq}"


@dataclass(frozen=True)
class Tanlovlar:
    """Yon paneldagi global tanlovlar."""

    metrika: str | None
    funk_nomi: str
    funk: str
    sana: str | None
    davr_nomi: str
    davr: str
    kategoriya: str | None
    top_n: int


class YonPanel:
    """Asosiy ko'rsatkich, agregatsiya, sana, davr va kategoriya tanlovlari."""

    def __init__(self, df: pd.DataFrame, profil: Profil, prefiks: str) -> None:
        self.df = df
        self.profil = profil
        self.prefiks = prefiks

    def _k(self, nom: str) -> str:
        return f"{self.prefiks}_{nom}"

    def _standart_metrika(self) -> int:
        """Nomida 'tushum', 'sotuv', 'summa' kabi so'z bo'lgan ustunni oldindan tanlaydi."""
        for i, ustun in enumerate(self.profil.raqamli):
            if any(k in ustun.lower() for k in Sozlamalar.KALIT_SOZLAR):
                return i
        return 0

    def _standart_davr(self, sana: str) -> int:
        """Sana oralig'i uzunligiga qarab mos davrni tanlaydi."""
        s = self.df[sana].dropna()
        kunlar = (s.max() - s.min()).days if len(s) else 0
        if kunlar <= 60:
            return 0
        if kunlar <= 240:
            return 1
        if kunlar <= 365 * 4:
            return 2
        return 4

    def sozlamalar(self) -> Tanlovlar:
        sb = st.sidebar
        p = self.profil
        sb.markdown("## ⚙️ Tahlil sozlamalari")

        metrika: str | None = None
        if p.raqamli:
            metrika = sb.selectbox(
                "📐 Asosiy ko'rsatkich", p.raqamli, index=self._standart_metrika(), key=self._k("metrika")
            )
            funk_nomi = sb.selectbox(
                "🧮 Agregatsiya turi", list(Sozlamalar.FUNKSIYALAR), key=self._k("funk")
            )
        else:
            sb.info("Raqamli ustun topilmadi — tahlil qatorlar soni bo'yicha bajariladi.")
            funk_nomi = "Soni"

        sana: str | None = None
        davr_nomi = "Oylik"
        if p.sanali:
            sana = sb.selectbox("📅 Sana ustuni", p.sanali, key=self._k("sana"))
            davr_nomi = sb.selectbox(
                "⏱️ Davr", list(Sozlamalar.DAVRLAR), index=self._standart_davr(sana), key=self._k("davr")
            )

        kat_royxati = [c for c in p.kategorik if c not in p.raqamli] + [c for c in p.kategorik if c in p.raqamli]
        kategoriya: str | None = None
        if kat_royxati:
            kategoriya = sb.selectbox(
                "🏷️ Asosiy kategoriya (kross-filtr shu ustun bo'yicha)", kat_royxati, key=self._k("kat")
            )
        top_n = sb.slider("🔝 Top-N kategoriya", 3, 30, 10, key=self._k("topn"))
        return Tanlovlar(
            metrika=metrika,
            funk_nomi=funk_nomi,
            funk=Sozlamalar.FUNKSIYALAR[funk_nomi],
            sana=sana,
            davr_nomi=davr_nomi,
            davr=Sozlamalar.DAVRLAR[davr_nomi],
            kategoriya=kategoriya,
            top_n=top_n,
        )


class FiltrPaneli:
    """Yon paneldagi dinamik filtrlar (sana, kategoriya, raqamli oraliq)."""

    def __init__(self, df: pd.DataFrame, profil: Profil, tanlov: Tanlovlar, prefiks: str) -> None:
        self.df = df
        self.profil = profil
        self.tanlov = tanlov
        self.prefiks = prefiks

    def _k(self, nom: str) -> str:
        return f"{self.prefiks}_f_{nom}"

    def qollash(self) -> pd.DataFrame:
        """Filtrlarni chizadi va filtrlangan jadvalni qaytaradi."""
        df, p = self.df, self.profil
        maska = pd.Series(True, index=df.index)

        with st.sidebar.expander("🎛️ Filtrlar", expanded=True):
            # --- sana oralig'i ---
            if self.tanlov.sana:
                s = df[self.tanlov.sana].dropna()
                if len(s):
                    mn, mx = s.min().date(), s.max().date()
                    oraliq = st.date_input(
                        "Sana oralig'i", value=(mn, mx), min_value=mn, max_value=mx, key=self._k("sana")
                    )
                    if isinstance(oraliq, (tuple, list)) and len(oraliq) == 2 and tuple(oraliq) != (mn, mx):
                        boshi = pd.Timestamp(oraliq[0])
                        oxiri = pd.Timestamp(oraliq[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                        maska &= df[self.tanlov.sana].between(boshi, oxiri)

            # --- kategorik filtrlar ---
            nomzodlar = [c for c in p.kategorik if c not in p.raqamli] or p.kategorik
            tanlangan_kat = st.multiselect(
                "Kategorik filtr ustunlari", nomzodlar, default=nomzodlar[:3], key=self._k("kat_ustunlar")
            )
            for ustun in tanlangan_kat:
                variantlar = sorted(df[ustun].dropna().astype(str).unique())
                tanlov = st.multiselect(ustun, variantlar, default=variantlar, key=self._k(f"kat_{ustun}"))
                if set(tanlov) != set(variantlar):
                    maska &= df[ustun].astype(str).isin(tanlov)

            # --- raqamli filtrlar ---
            if p.raqamli:
                tanlangan_raqam = st.multiselect(
                    "Raqamli filtr ustunlari", p.raqamli, default=p.raqamli[:1], key=self._k("raqam_ustunlar")
                )
                for ustun in tanlangan_raqam:
                    s = df[ustun].dropna()
                    if s.empty or s.min() == s.max():
                        continue
                    mn, mx = float(s.min()), float(s.max())
                    lo, hi = st.slider(
                        ustun, mn, mx, (mn, mx), step=(mx - mn) / 200, key=self._k(f"raqam_{ustun}")
                    )
                    if (lo, hi) != (mn, mx):
                        maska &= df[ustun].between(lo, hi)

        return df[maska]


# =============================================================================
# 5. KROSS-FILTR (grafikni bosish orqali bog'lash)
# =============================================================================
def kross_kalit(prefiks: str, ustun: str | None) -> str:
    """Kross-filtr grafigi uchun barqaror vidjet kaliti (tozalash sanagichi bilan)."""
    return f"kross_{prefiks}_{ustun}_{st.session_state.get('tozalash_soni', 0)}"


def tanlangan_qiymatlar(kalit: str) -> list[str]:
    """Kross-filtr grafigida bosilgan kategoriyalar ro'yxati."""
    holat = st.session_state.get(kalit)
    if not holat:
        return []
    try:
        nuqtalar = holat["selection"]["points"]
    except (KeyError, TypeError):
        return []
    return [str(n["y"]) for n in nuqtalar if isinstance(n, dict) and "y" in n]


# =============================================================================
# 6. AQLLI XULOSALAR
# =============================================================================
class AqlliXulosalar:
    """Ma'lumotga qarab avtomatik matnli xulosalar (insight) yaratadi."""

    def __init__(self, df: pd.DataFrame, profil: Profil, tanlov: Tanlovlar) -> None:
        self.df = df
        self.profil = profil
        self.t = tanlov

    def yaratish(self) -> list[tuple[str, str]]:
        """[(ikonka, HTML matn), ...] ro'yxatini qaytaradi."""
        natija: list[tuple[str, str]] = []
        for usul in (self._kategoriya, self._trend, self._hafta_kuni, self._korrelyatsiya,
                     self._chetlashma, self._yetishmagan, self._assimetriya):
            try:
                natija.extend(usul())
            except Exception:  # noqa: BLE001 - bitta xulosa xato bersa, qolganlari ishlayveradi
                continue
        return natija or [("ℹ️", "Xulosa chiqarish uchun ma'lumot yetarli emas.")]

    def _kategoriya(self) -> list[tuple[str, str]]:
        t, e = self.t, html.escape
        if not t.kategoriya or self.df.empty:
            return []
        d = agregatsiya(self.df, t.kategoriya, t.metrika, t.funk).sort_values("Qiymat", ascending=False)
        jami = d["Qiymat"].clip(lower=0).sum()
        if d.empty or jami <= 0:
            return []
        birinchi = d.iloc[0]
        ulush = max(birinchi["Qiymat"], 0) / jami * 100
        chiqish = [("🏆", f"<b>{e(str(birinchi[t.kategoriya]))}</b> — «{e(t.kategoriya)}» bo'yicha yetakchi "
                          f"({qisqa_raqam_html(birinchi['Qiymat'])}, umumiyning <b>{ulush:.1f}%</b> qismi).")]
        kum = d["Qiymat"].clip(lower=0).cumsum() / jami
        n80 = int((kum < 0.8).sum() + 1)
        if len(d) >= 5:
            chiqish.append(("⚖️", f"Pareto: natijaning 80% qismini <b>{n80} ta</b> kategoriya "
                                  f"({n80 / len(d) * 100:.0f}%) beradi. Qolgan {len(d) - n80} tasi kichik hissa qo'shadi."))
        return chiqish

    def _trend(self) -> list[tuple[str, str]]:
        t = self.t
        if not t.sana:
            return []
        q = vaqt_qatori(self.df, t.sana, t.metrika, t.funk, t.davr).dropna()
        if len(q) < 4:
            return []
        y = q["Qiymat"].to_numpy(dtype=float)
        x = np.arange(len(y))
        egim = np.polyfit(x, y, 1)[0]
        ortacha = abs(y.mean()) or 1.0
        umumiy = egim * (len(y) - 1) / ortacha * 100
        yonalish = "o'sish 📈" if umumiy > 3 else ("pasayish 📉" if umumiy < -3 else "barqaror holat ➖")
        eng_yuqori, eng_past = q.loc[q["Qiymat"].idxmax()], q.loc[q["Qiymat"].idxmin()]
        variatsiya = y.std() / ortacha
        barqarorlik = "yuqori tebranish" if variatsiya > 0.5 else "nisbatan barqaror"
        return [
            ("📈", f"Umumiy tendensiya: <b>{yonalish}</b> (davr boshidan oxirigacha taxminan <b>{umumiy:+.1f}%</b>)."),
            ("📅", f"Eng yuqori davr: <b>{davr_yorligi(eng_yuqori[t.sana], t.davr_nomi)}</b> "
                   f"({qisqa_raqam_html(eng_yuqori['Qiymat'])}); eng past: "
                   f"<b>{davr_yorligi(eng_past[t.sana], t.davr_nomi)}</b> ({qisqa_raqam_html(eng_past['Qiymat'])})."),
            ("🌊", f"Tebranish darajasi: <b>{barqarorlik}</b> (variatsiya koeffitsienti {variatsiya:.2f})."),
        ]

    def _hafta_kuni(self) -> list[tuple[str, str]]:
        t = self.t
        if not t.sana or self.df[t.sana].dropna().nunique() < 14:
            return []
        d = self.df.dropna(subset=[t.sana]).assign(_kun=lambda x: x[t.sana].dt.dayofweek)
        a = agregatsiya(d, "_kun", t.metrika, t.funk)
        if len(a) < 5:
            return []
        eng = a.loc[a["Qiymat"].idxmax()]
        return [("🗓️", f"Hafta kunlari ichida eng faol kun: <b>{Sozlamalar.HAFTA_KUNLARI[int(eng['_kun'])]}</b>.")]

    def _korrelyatsiya(self) -> list[tuple[str, str]]:
        raqamli = self.profil.raqamli[:40]
        if len(raqamli) < 2:
            return []
        kor = self.df[raqamli].corr(numeric_only=True)
        juftlar: list[tuple[float, str, str, float]] = []
        for i, a in enumerate(kor.columns):
            for b in kor.columns[i + 1:]:
                r = kor.loc[a, b]
                if pd.notna(r) and abs(r) >= 0.6:
                    juftlar.append((abs(r), a, b, float(r)))
        chiqish = []
        for _, a, b, r in sorted(juftlar, reverse=True)[:3]:
            turi = "musbat" if r > 0 else "manfiy"
            chiqish.append(("🔗", f"<b>{html.escape(a)}</b> va <b>{html.escape(b)}</b> o'rtasida kuchli "
                                  f"{turi} bog'liqlik (r = {r:.2f})."))
        return chiqish

    def _chetlashma(self) -> list[tuple[str, str]]:
        jadval = chetlashmalar_jadvali(self.df, self.profil.raqamli)
        if jadval.empty:
            return []
        q = jadval.iloc[0]
        return [("🚨", f"<b>{html.escape(str(q['Ustun']))}</b> ustunida <b>{int(q['Chetlashmalar soni'])}</b> ta "
                       f"chetlashma bor ({q['Ulushi (%)']}%). «Xulosalar» yorlig'idan batafsil ko'ring.")]

    def _yetishmagan(self) -> list[tuple[str, str]]:
        foiz = self.df.isna().mean() * 100
        yomon = foiz[foiz > 10].sort_values(ascending=False).head(3)
        return [("🕳️", f"<b>{html.escape(str(u))}</b> ustunida qiymatlarning <b>{v:.1f}%</b> yetishmayapti.")
                for u, v in yomon.items()]

    def _assimetriya(self) -> list[tuple[str, str]]:
        chiqish = []
        for ustun in self.profil.raqamli[:15]:
            s = self.df[ustun].dropna()
            if len(s) > 30 and s.nunique() > 12 and abs(s.skew()) > 1.5:
                chiqish.append(("📐", f"<b>{html.escape(ustun)}</b> taqsimoti keskin assimetrik (skew = {s.skew():.2f}); "
                                      f"bunday ustun uchun o'rtachadan ko'ra <b>medyana</b> ishonchliroq."))
        return chiqish[:2]


def qisqa_raqam_html(x: float) -> str:
    """HTML xavfsiz qisqa raqam."""
    return html.escape(qisqa_raqam(x))


# =============================================================================
# 7. GRAFIKLAR FABRIKASI
# =============================================================================
class GrafikFabrikasi:
    """Barcha Plotly grafiklarini yaratuvchi statik metodlar to'plami."""

    @staticmethod
    def bezash(fig: go.Figure, sarlavha: str = "", balandlik: int = 380) -> go.Figure:
        """Barcha grafiklar uchun yagona uslub."""
        fig.update_layout(
            title=dict(text=sarlavha, x=0.01, font=dict(size=16)),
            height=balandlik,
            margin=dict(l=10, r=10, t=55, b=10),
            legend=dict(orientation="h", y=-0.18, x=0),
            font=dict(family="Inter, Segoe UI, sans-serif"),
            colorway=Sozlamalar.PALITRA,
            hoverlabel=dict(font_size=13),
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(128,128,128,.18)")
        return fig

    @staticmethod
    def trend(qator: pd.DataFrame, sana: str, nom: str, davr: str,
              oyna: int = 3, anomaliya: bool = True, prognoz: int = 0) -> go.Figure:
        """Vaqt qatori: asosiy chiziq, harakatlanuvchi o'rtacha, anomaliyalar va prognoz."""
        x, y = qator[sana], qator["Qiymat"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers" if len(qator) <= 60 else "lines", name=nom,
            line=dict(color=Sozlamalar.RANG_ASOSIY, width=3), marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(108,99,255,.12)",
        ))
        if oyna > 1 and len(qator) > oyna:
            fig.add_trace(go.Scatter(
                x=x, y=y.rolling(oyna, min_periods=1).mean(), mode="lines",
                name=f"Harakatlanuvchi o'rtacha ({oyna})", line=dict(color="#FFB020", width=2.5, dash="dot"),
            ))
        if anomaliya and y.std(ddof=0) > 0:
            z = (y - y.mean()) / y.std(ddof=0)
            m = z.abs() > 2.5
            if m.any():
                fig.add_trace(go.Scatter(
                    x=x[m], y=y[m], mode="markers", name="Anomaliya",
                    marker=dict(color="#EF4444", size=12, symbol="diamond", line=dict(color="white", width=1.5)),
                ))
        if prognoz > 0 and y.notna().sum() >= 4:
            t = np.arange(len(y))
            ok = y.notna().to_numpy()
            koef = np.polyfit(t[ok], y.to_numpy()[ok], 1)
            kelajak_t = np.arange(len(y) - 1, len(y) + prognoz)
            kelajak_x = pd.date_range(x.iloc[-1], periods=prognoz + 1, freq=davr)
            fig.add_trace(go.Scatter(
                x=kelajak_x, y=np.polyval(koef, kelajak_t), mode="lines+markers", name="Prognoz (chiziqli)",
                line=dict(color="#00C2A8", width=2.5, dash="dash"),
            ))
        return GrafikFabrikasi.bezash(fig, f"{nom} — vaqt bo'yicha dinamika", 400)

    @staticmethod
    def ozgarish(qator: pd.DataFrame, sana: str) -> go.Figure:
        """Davrdan davrga foizli o'zgarish."""
        o = qator["Qiymat"].pct_change().replace([np.inf, -np.inf], np.nan) * 100
        ranglar = ["#22C55E" if (pd.notna(v) and v >= 0) else "#EF4444" for v in o]
        fig = go.Figure(go.Bar(x=qator[sana], y=o, marker_color=ranglar, name="O'zgarish"))
        fig.update_yaxes(ticksuffix="%")
        return GrafikFabrikasi.bezash(fig, "Davrdan davrga o'zgarish (%)", 320)

    @staticmethod
    def top_bar(d: pd.DataFrame, ustun: str, nom: str, top_n: int) -> go.Figure:
        """Gorizontal ustunli grafik (kross-filtr uchun ham ishlatiladi)."""
        d = d.sort_values("Qiymat", ascending=False).head(top_n).sort_values("Qiymat").copy()
        d[ustun] = d[ustun].astype(str)
        fig = px.bar(d, x="Qiymat", y=ustun, orientation="h", color="Qiymat",
                     color_continuous_scale=["#C7C3FF", Sozlamalar.RANG_ASOSIY, "#2D2A8C"])
        fig.update_traces(texttemplate="%{x:.3s}", textposition="outside", cliponaxis=False)
        fig.update_yaxes(type="category", title=None)
        fig.update_xaxes(title=None)
        fig.update_coloraxes(showscale=False)
        return GrafikFabrikasi.bezash(fig, f"Top-{top_n}: {ustun} bo'yicha {nom}", 400)

    @staticmethod
    def donut(d: pd.DataFrame, ustun: str, top_n: int) -> go.Figure:
        """Ulushlar uchun donut grafik (kichiklari 'Boshqalar'ga yig'iladi)."""
        d = d[d["Qiymat"] > 0].sort_values("Qiymat", ascending=False)
        bosh, qolgan = d.head(top_n).copy(), d.iloc[top_n:]["Qiymat"].sum()
        bosh[ustun] = bosh[ustun].astype(str)
        if qolgan > 0:
            bosh = pd.concat([bosh, pd.DataFrame({ustun: ["Boshqalar"], "Qiymat": [qolgan]})], ignore_index=True)
        fig = go.Figure(go.Pie(labels=bosh[ustun], values=bosh["Qiymat"], hole=0.58,
                               marker=dict(colors=Sozlamalar.PALITRA), textinfo="percent"))
        return GrafikFabrikasi.bezash(fig, f"Ulushlar: {ustun}", 400)

    @staticmethod
    def pareto(d: pd.DataFrame, ustun: str) -> go.Figure:
        """Pareto diagrammasi: ustunlar + kumulyativ ulush chizig'i."""
        d = d[d["Qiymat"] > 0].sort_values("Qiymat", ascending=False).head(25).copy()
        jami = d["Qiymat"].sum() or 1
        d["Kum"] = d["Qiymat"].cumsum() / jami * 100
        d[ustun] = d[ustun].astype(str)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=d[ustun], y=d["Qiymat"], name="Qiymat", marker_color=Sozlamalar.RANG_ASOSIY), secondary_y=False)
        fig.add_trace(go.Scatter(x=d[ustun], y=d["Kum"], name="Kumulyativ %", mode="lines+markers",
                                 line=dict(color="#FF6584", width=3)), secondary_y=True)
        fig.add_hline(y=80, line_dash="dot", line_color="#FFB020", secondary_y=True)
        fig.update_yaxes(range=[0, 105], ticksuffix="%", secondary_y=True, showgrid=False)
        return GrafikFabrikasi.bezash(fig, f"Pareto tahlili (80/20): {ustun}", 400)

    @staticmethod
    def hafta_kuni(d: pd.DataFrame) -> go.Figure:
        """Hafta kunlari bo'yicha ustunli grafik. `d` — '_kun' va 'Qiymat' ustunlari."""
        d = d.set_index("_kun").reindex(range(7)).reset_index()
        d["Kun"] = Sozlamalar.HAFTA_KUNLARI
        fig = px.bar(d, x="Kun", y="Qiymat", color="Qiymat", color_continuous_scale=["#C7C3FF", "#6C63FF", "#2D2A8C"])
        fig.update_coloraxes(showscale=False)
        fig.update_xaxes(title=None)
        return GrafikFabrikasi.bezash(fig, "Hafta kunlari bo'yicha", 340)

    @staticmethod
    def issiqlik_hafta_oy(d: pd.DataFrame) -> go.Figure:
        """Hafta kuni × oy issiqlik xaritasi. `d` — '_kun', '_oy', 'Qiymat'."""
        jadval = d.pivot(index="_kun", columns="_oy", values="Qiymat").reindex(index=range(7), columns=range(1, 13))
        fig = go.Figure(go.Heatmap(
            z=jadval.values, x=Sozlamalar.OYLAR, y=Sozlamalar.HAFTA_KUNLARI,
            colorscale="Purples", hoverongaps=False, colorbar=dict(thickness=12),
        ))
        fig.update_yaxes(autorange="reversed")
        return GrafikFabrikasi.bezash(fig, "Faollik xaritasi: hafta kuni × oy", 340)

    @staticmethod
    def treemap(d: pd.DataFrame, yol: list[str]) -> go.Figure:
        """Ierarxik ulushlar (treemap)."""
        d = d[d["Qiymat"] > 0].copy()
        for ustun in yol:
            d[ustun] = d[ustun].astype(str)
        fig = px.treemap(d, path=yol, values="Qiymat", color_discrete_sequence=Sozlamalar.PALITRA)
        fig.update_traces(textinfo="label+percent parent")
        return GrafikFabrikasi.bezash(fig, "Ierarxik tuzilma (treemap)", 440)

    @staticmethod
    def box(df: pd.DataFrame, kat: str, metrika: str, top: list[str]) -> go.Figure:
        """Kategoriyalar bo'yicha taqsimot (box-plot)."""
        d = df[[kat, metrika]].dropna().copy()
        d[kat] = d[kat].astype(str)
        d = d[d[kat].isin(top)]
        fig = px.box(d, x=kat, y=metrika, color=kat, color_discrete_sequence=Sozlamalar.PALITRA)
        fig.update_layout(showlegend=False)
        return GrafikFabrikasi.bezash(fig, f"{metrika} taqsimoti: {kat} bo'yicha", 400)

    @staticmethod
    def pivot_issiqlik(d: pd.DataFrame, a: str, b: str) -> go.Figure:
        """Ikki kategoriya kesishmasi issiqlik xaritasi."""
        d = d.copy()
        d[a], d[b] = d[a].astype(str), d[b].astype(str)
        jadval = d.pivot(index=a, columns=b, values="Qiymat")
        fig = px.imshow(jadval, text_auto=".3s", aspect="auto", color_continuous_scale="Purples")
        fig.update_coloraxes(showscale=False)
        return GrafikFabrikasi.bezash(fig, f"Kesishma: {a} × {b}", 420)

    @staticmethod
    def gistogramma(df: pd.DataFrame, ustun: str) -> go.Figure:
        """Gistogramma + yuqorida box-plot."""
        fig = px.histogram(df, x=ustun, nbins=40, marginal="box", color_discrete_sequence=[Sozlamalar.RANG_ASOSIY])
        fig.update_layout(bargap=0.04)
        return GrafikFabrikasi.bezash(fig, f"{ustun} taqsimoti", 420)

    @staticmethod
    def korrelyatsiya(df: pd.DataFrame, raqamli: list[str]) -> go.Figure:
        """Korrelyatsiya matritsasi issiqlik xaritasi."""
        kor = df[raqamli[:25]].corr(numeric_only=True)
        fig = px.imshow(kor, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        return GrafikFabrikasi.bezash(fig, "Korrelyatsiya matritsasi", 480)

    @staticmethod
    def sochma(df: pd.DataFrame, x: str, y: str, rang: str | None, olcham: str | None) -> tuple[go.Figure, float]:
        """Scatter + chiziqli trend. (grafik, korrelyatsiya koeffitsienti) qaytaradi."""
        ustunlar = list(dict.fromkeys([x, y] + ([rang] if rang else []) + ([olcham] if olcham else [])))
        d = df[ustunlar].dropna()
        if len(d) > 5000:
            d = d.sample(5000, random_state=1)
        d = d.copy()
        if rang:
            d[rang] = d[rang].astype(str)
        if olcham:
            d[olcham] = d[olcham].clip(lower=0)
        fig = px.scatter(d, x=x, y=y, color=rang, size=olcham, opacity=0.7,
                         color_discrete_sequence=Sozlamalar.PALITRA)
        r = float("nan")
        if len(d) >= 3 and d[x].std() > 0 and x != y:
            k = np.polyfit(d[x], d[y], 1)
            xs = np.array([d[x].min(), d[x].max()])
            fig.add_trace(go.Scatter(x=xs, y=np.polyval(k, xs), mode="lines", name="Trend",
                                     line=dict(color="#EF4444", dash="dash", width=2.5)))
            r = float(d[x].corr(d[y]))
        return GrafikFabrikasi.bezash(fig, f"{x} va {y} munosabati", 460), r

    @staticmethod
    def yetishmagan(df: pd.DataFrame) -> go.Figure:
        """Ustunlar bo'yicha yetishmayotgan qiymatlar foizi."""
        foiz = (df.isna().mean() * 100).sort_values()
        foiz = foiz[foiz > 0]
        fig = go.Figure(go.Bar(x=foiz.values, y=foiz.index.astype(str), orientation="h", marker_color="#FF6584"))
        fig.update_xaxes(ticksuffix="%")
        return GrafikFabrikasi.bezash(fig, "Yetishmayotgan qiymatlar (%)", max(260, 40 * len(foiz) + 100))



CSS = """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px;}
.hero {background: linear-gradient(120deg,#4F46E5 0%,#7C3AED 55%,#EC4899 100%); color:#fff;
       padding: 22px 28px; border-radius: 22px; margin-bottom: 18px;
       box-shadow: 0 10px 30px rgba(79,70,229,.30);}
.hero h1 {margin:0; font-size: 1.9rem; font-weight: 800; color:#fff;}
.hero p {margin: 6px 0 0 0; opacity:.92; font-size:.95rem;}
.kpi {border-radius: 18px; padding: 15px 17px 12px 17px; color:#fff; min-height: 142px; position: relative;
      box-shadow: 0 8px 22px rgba(0,0,0,.16); overflow: hidden; transition: transform .2s ease;}
.kpi:hover {transform: translateY(-4px);}
.kpi .ikonka {position:absolute; right: 14px; top: 10px; font-size: 1.6rem; opacity:.85;}
.kpi .sarlavha {font-size:.78rem; font-weight:600; opacity:.9; letter-spacing:.3px; padding-right: 34px;}
.kpi .qiymat {font-size:1.65rem; font-weight:800; margin: 4px 0 2px 0; line-height:1.15; word-break: break-word;}
.kpi .izoh {font-size:.76rem; opacity:.93;}
.kpi .spark {margin-top: 4px; height: 34px;}
.pill {display:inline-block; padding: 1px 8px; border-radius: 999px; font-weight:700; margin-right:4px;
       background: rgba(255,255,255,.22);}
.pill.up {background: rgba(34,197,94,.85);} .pill.down {background: rgba(239,68,68,.88);}
.insight {display:flex; gap:12px; align-items:flex-start; padding: 12px 16px; margin-bottom: 10px;
          border-radius: 14px; border-left: 5px solid #6C63FF; background: rgba(108,99,255,.09);}
.insight .e {font-size:1.3rem;}
.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [data-baseweb="tab"] {border-radius: 12px 12px 0 0; padding: 8px 16px; font-weight: 600;}
</style>
"""


def kpi_karta(sarlavha: str, qiymat: str, izoh: str, gradient: str, ikonka: str,
              delta: float | None = None, spark: str = "") -> str:
    """Bitta KPI kartaning HTML kodi (bir qatorda, ichki bo'shliqsiz)."""
    delta_html = ""
    if delta is not None and np.isfinite(delta):
        sinf, belgi = ("up", "▲") if delta >= 0 else ("down", "▼")
        delta_html = f'<span class="pill {sinf}">{belgi} {abs(delta):.1f}%</span>'
    return (
        f'<div class="kpi" style="background:{gradient}">'
        f'<div class="ikonka">{ikonka}</div>'
        f'<div class="sarlavha">{html.escape(sarlavha)}</div>'
        f'<div class="qiymat">{html.escape(qiymat)}</div>'
        f'<div class="izoh">{delta_html}{html.escape(izoh)}</div>'
        f'<div class="spark">{spark}</div></div>'
    )


class Dashboard:
    """Hamma bo'limlarni bir joyga yig'uvchi asosiy sinf."""

    def __init__(self, asl: pd.DataFrame, filtrli: pd.DataFrame, kross: pd.DataFrame,
                 profil: Profil, tanlov: Tanlovlar, nom: str, prefiks: str) -> None:
        self.asl = asl              # hech qanday filtrsiz jadval
        self.filtrli = filtrli      # yon panel filtrlari qo'llangan jadval
        self.df = kross             # + kross-filtr qo'llangan jadval (asosiy ish jadvali)
        self.p = profil
        self.t = tanlov
        self.nom = nom
        self.prefiks = prefiks
        self.ko_rsatkich_nomi = f"{tanlov.funk_nomi}: {tanlov.metrika}" if tanlov.metrika else "Qatorlar soni"
        self.qator = (
            vaqt_qatori(self.df, tanlov.sana, tanlov.metrika, tanlov.funk, tanlov.davr)
            if tanlov.sana else None
        )

    def _k(self, nom: str) -> str:
        return f"{self.prefiks}_d_{nom}"

    # ------------------------------------------------------------------ umumiy
    def chizish(self) -> None:
        self._sarlavha()
        self._kross_xabari()
        self._kpi_kartalar()
        self._asosiy_qator()
        yorliqlar = st.tabs([
            "📈 Vaqt tahlili", "🧩 Kategoriyalar", "🔬 Taqsimot va bog'liqlik",
            "💡 Aqlli xulosalar", "🧪 Ma'lumot sifati", "🗂️ Jadval",
        ])
        with yorliqlar[0]:
            self._tab_vaqt()
        with yorliqlar[1]:
            self._tab_kategoriya()
        with yorliqlar[2]:
            self._tab_taqsimot()
        with yorliqlar[3]:
            self._tab_xulosalar()
        with yorliqlar[4]:
            self._tab_sifat()
        with yorliqlar[5]:
            self._tab_jadval()

    def _sarlavha(self) -> None:
        st.markdown(
            f'<div class="hero"><h1>{Sozlamalar.IKONKA} {Sozlamalar.SAHIFA_NOMI}</h1>'
            f'<p>📁 {html.escape(self.nom)} &nbsp;•&nbsp; {len(self.asl):,} qator &nbsp;•&nbsp; '
            f'{self.asl.shape[1]} ustun &nbsp;•&nbsp; Ko\'rsatkich: <b>{html.escape(self.ko_rsatkich_nomi)}</b></p></div>',
            unsafe_allow_html=True,
        )

    def _kross_xabari(self) -> None:
        """Kross-filtr faol bo'lsa, xabar va tozalash tugmasini ko'rsatadi."""
        if len(self.df) == len(self.filtrli) and self.filtrli is not self.df and not self._kross_faol:
            return
        if not self._kross_faol:
            return
        c1, c2 = st.columns([6, 1])
        c1.info(f"🔗 Kross-filtr faol: **{self.t.kategoriya}** = {', '.join(self._kross_qiymatlar)} "
                f"— barcha KPI va grafiklar shu tanlovga moslashgan.")
        if c2.button("✖ Tozalash", width="stretch"):
            st.session_state["tozalash_soni"] = st.session_state.get("tozalash_soni", 0) + 1
            st.rerun()

    _kross_faol: bool = False
    _kross_qiymatlar: list[str] = []

    # --------------------------------------------------------------------- KPI
    def _kpi_kartalar(self) -> None:
        d, t = self.df, self.t
        sifat = sifat_bahosi(self.asl)
        asosiy = skalyar(d, t.metrika, t.funk)
        delta: float | None = None
        spark = ""
        if self.qator is not None and len(self.qator) >= 2:
            oxirgi, oldingi = self.qator["Qiymat"].iloc[-1], self.qator["Qiymat"].iloc[-2]
            if pd.notna(oxirgi) and pd.notna(oldingi) and oldingi != 0:
                delta = float((oxirgi - oldingi) / abs(oldingi) * 100)
            spark = sparkline_svg(self.qator["Qiymat"])

        # 3-karta: davr o'rtachasi yoki qator o'rtachasi; 4-karta: eng yuqori davr yoki maksimum
        if self.qator is not None and len(self.qator):
            uchinchi = ("Davr o'rtachasi", qisqa_raqam(self.qator["Qiymat"].mean()), f"{t.davr_nomi} bo'yicha", "🎯")
            if self.qator["Qiymat"].notna().any():
                eng = self.qator.loc[self.qator["Qiymat"].idxmax()]
                turtinchi = ("Eng yuqori davr", qisqa_raqam(eng["Qiymat"]), davr_yorligi(eng[t.sana], t.davr_nomi), "🚀")
            else:
                turtinchi = ("Eng yuqori davr", "—", "", "🚀")
        elif t.metrika:
            uchinchi = ("O'rtacha (qator)", qisqa_raqam(d[t.metrika].mean()), t.metrika, "🎯")
            turtinchi = ("Maksimum", qisqa_raqam(d[t.metrika].max()), t.metrika, "🚀")
        else:
            uchinchi = ("Ustunlar", str(self.asl.shape[1]), "jadvaldagi ustunlar", "🎯")
            turtinchi = ("Kategoriyalar", str(len(self.p.kategorik)), "kategorik ustunlar", "🚀")

        beshinchi = ("Yetakchi kategoriya", "—", "", "🏆")
        if t.kategoriya and not d.empty:
            a = agregatsiya(d, t.kategoriya, t.metrika, t.funk)
            if not a.empty:
                top = a.loc[a["Qiymat"].idxmax()]
                jami = a["Qiymat"].clip(lower=0).sum()
                ulush = f"ulushi {max(top['Qiymat'], 0) / jami * 100:.1f}%" if jami > 0 else t.kategoriya
                nom = str(top[t.kategoriya])
                beshinchi = (f"Yetakchi: {t.kategoriya}", nom if len(nom) <= 18 else nom[:16] + "…", ulush, "🏆")

        kartalar = [
            ("Tanlangan qatorlar", f"{len(d):,}", f"jami {len(self.asl):,} ning {len(d) / max(len(self.asl), 1) * 100:.1f}%",
             "🧾", None, ""),
            (self.ko_rsatkich_nomi, qisqa_raqam(asosiy), "oxirgi davr vs oldingi" if delta is not None else "umumiy",
             "💰", delta, spark),
            (*uchinchi, None, ""),
            (*turtinchi, None, ""),
            (*beshinchi, None, ""),
            ("Ma'lumot sifati", f"{sifat['ball']:.0f}/100", f"yetishmagan {sifat['yetishmagan']:.1f}% • takror {sifat['takror']:.1f}%",
             "🛡️", None, ""),
        ]
        for ustun, (sarlavha, qiymat, izoh, ikonka, dl, sp), grad in zip(
            st.columns(6), kartalar, Sozlamalar.GRADIENTLAR
        ):
            ustun.markdown(kpi_karta(sarlavha, qiymat, izoh, grad, ikonka, dl, sp), unsafe_allow_html=True)
        st.write("")

    # ------------------------------------------------------------ asosiy qator
    def _asosiy_qator(self) -> None:
        t = self.t
        chap, ong = st.columns([3, 2])
        with chap:
            if self.qator is not None and len(self.qator):
                fig = GrafikFabrikasi.trend(self.qator, t.sana, self.ko_rsatkich_nomi, t.davr, oyna=3, anomaliya=True)
                st.plotly_chart(fig, width="stretch", key=self._k("asosiy_trend"))
            elif t.metrika:
                st.plotly_chart(GrafikFabrikasi.gistogramma(self.df, t.metrika), width="stretch",
                                key=self._k("asosiy_gist"))
            else:
                st.info("Sana yoki raqamli ustun topilmadi.")
        with ong:
            if t.kategoriya:
                d = agregatsiya(self.filtrli, t.kategoriya, t.metrika, t.funk)
                fig = GrafikFabrikasi.top_bar(d, t.kategoriya, self.ko_rsatkich_nomi, t.top_n)
                st.plotly_chart(
                    fig, width="stretch", key=kross_kalit(self.prefiks, t.kategoriya),
                    on_select="rerun", selection_mode="points",
                )
                st.caption("🔗 **Kross-filtr:** ustunni bosing — butun panel shu kategoriyaga moslashadi "
                           "(bir nechtasini tanlash uchun Shift bilan bosing).")
            else:
                st.info("Kategorik ustun topilmadi.")

    # --------------------------------------------------------------- vaqt tahlili
    def _tab_vaqt(self) -> None:
        t = self.t
        if self.qator is None or self.qator.empty:
            st.info("Vaqt tahlili uchun sana ustuni topilmadi.")
            return
        c1, c2, c3 = st.columns(3)
        oyna = c1.slider("Harakatlanuvchi o'rtacha oynasi", 1, 12, 3, key=self._k("oyna"))
        anomaliya = c2.checkbox("Anomaliyalarni belgilash", value=True, key=self._k("anom"))
        prognoz = c3.slider("Prognoz davrlari soni", 0, 12, 0, key=self._k("prog"))
        st.plotly_chart(
            GrafikFabrikasi.trend(self.qator, t.sana, self.ko_rsatkich_nomi, t.davr, oyna, anomaliya, prognoz),
            width="stretch", key=self._k("vaqt_trend"),
        )
        if len(self.qator) >= 3:
            st.plotly_chart(GrafikFabrikasi.ozgarish(self.qator, t.sana), width="stretch",
                            key=self._k("vaqt_ozgarish"))

        d = self.df.dropna(subset=[t.sana]).assign(
            _kun=lambda x: x[t.sana].dt.dayofweek, _oy=lambda x: x[t.sana].dt.month
        )
        if d.empty:
            return
        a, b = st.columns(2)
        a.plotly_chart(GrafikFabrikasi.hafta_kuni(agregatsiya(d, "_kun", t.metrika, t.funk)), width="stretch",
                       key=self._k("vaqt_hafta"))
        b.plotly_chart(
            GrafikFabrikasi.issiqlik_hafta_oy(agregatsiya(d, ["_kun", "_oy"], t.metrika, t.funk)), width="stretch",
            key=self._k("vaqt_issiqlik"),
        )

    # -------------------------------------------------------------- kategoriyalar
    def _tab_kategoriya(self) -> None:
        t, p = self.t, self.p
        variantlar = [c for c in p.kategorik if c not in p.raqamli] + [c for c in p.kategorik if c in p.raqamli]
        if not variantlar:
            st.info("Kategorik ustun topilmadi.")
            return
        boshlang = variantlar.index(t.kategoriya) if t.kategoriya in variantlar else 0
        kat = st.selectbox("Kategoriya ustuni", variantlar, index=boshlang, key=self._k("tabkat"))
        d = agregatsiya(self.df, kat, t.metrika, t.funk)
        if d.empty:
            st.warning("Tanlangan qism bo'sh.")
            return

        a, b = st.columns([3, 2])
        a.plotly_chart(GrafikFabrikasi.pareto(d, kat), width="stretch", key=self._k(f"kat_pareto_{kat}"))
        b.plotly_chart(GrafikFabrikasi.donut(d, kat, min(t.top_n, 8)), width="stretch",
                       key=self._k(f"kat_donut_{kat}"))

        st.markdown("##### 🌳 Ierarxik ko'rinish va kesishmalar")
        boshqalar = [c for c in variantlar if c != kat]
        ikkinchi = st.selectbox("Ikkinchi kategoriya (ixtiyoriy)", [None] + boshqalar,
                                format_func=lambda x: "— tanlanmagan —" if x is None else x, key=self._k("kat2"))
        if ikkinchi:
            d2 = agregatsiya(self.df.dropna(subset=[kat, ikkinchi]), [kat, ikkinchi], t.metrika, t.funk)
            c1, c2 = st.columns(2)
            c1.plotly_chart(GrafikFabrikasi.treemap(d2, [kat, ikkinchi]), width="stretch",
                            key=self._k(f"kat_treemap_{kat}_{ikkinchi}"))
            if d2[kat].nunique() <= 30 and d2[ikkinchi].nunique() <= 30:
                c2.plotly_chart(GrafikFabrikasi.pivot_issiqlik(d2, kat, ikkinchi), width="stretch",
                                key=self._k(f"kat_pivot_{kat}_{ikkinchi}"))
        else:
            st.plotly_chart(GrafikFabrikasi.treemap(d, [kat]), width="stretch", key=self._k(f"kat_treemap_{kat}"))

        if t.metrika:
            top = (self.df[kat].astype(str).value_counts().head(t.top_n).index.tolist())
            st.plotly_chart(GrafikFabrikasi.box(self.df, kat, t.metrika, top), width="stretch",
                            key=self._k(f"kat_box_{kat}"))

    # ----------------------------------------------------------------- taqsimot
    def _tab_taqsimot(self) -> None:
        p = self.p
        if not p.raqamli:
            st.info("Raqamli ustun topilmadi.")
            return
        ustun = st.selectbox("Raqamli ustun", p.raqamli,
                             index=p.raqamli.index(self.t.metrika) if self.t.metrika in p.raqamli else 0,
                             key=self._k("gist"))
        s = self.df[ustun].dropna()
        if s.empty:
            st.warning("Tanlangan qismda qiymat yo'q.")
            return
        m = st.columns(5)
        for k, (nom, qiy) in zip(m, [("O'rtacha", s.mean()), ("Medyana", s.median()), ("Std. og'ish", s.std()),
                                     ("Minimum", s.min()), ("Maksimum", s.max())]):
            k.metric(nom, qisqa_raqam(qiy))
        st.plotly_chart(GrafikFabrikasi.gistogramma(self.df, ustun), width="stretch",
                        key=self._k(f"taqs_gist_{ustun}"))

        if len(p.raqamli) >= 2:
            st.markdown("##### 🔗 Bog'liqlik tahlili")
            st.plotly_chart(GrafikFabrikasi.korrelyatsiya(self.df, p.raqamli), width="stretch",
                            key=self._k("taqs_korrelyatsiya"))
            c1, c2, c3, c4 = st.columns(4)
            x = c1.selectbox("X o'qi", p.raqamli, key=self._k("sx"))
            y = c2.selectbox("Y o'qi", p.raqamli, index=1, key=self._k("sy"))
            rang = c3.selectbox("Rang (kategoriya)", [None] + [c for c in p.kategorik if c not in (x, y)],
                                format_func=lambda v: "— yo'q —" if v is None else v, key=self._k("srang"))
            olcham = c4.selectbox("O'lcham (raqamli)", [None] + [c for c in p.raqamli if c not in (x, y)],
                                  format_func=lambda v: "— yo'q —" if v is None else v, key=self._k("solcham"))
            fig, r = GrafikFabrikasi.sochma(self.df, x, y, rang, olcham)
            st.plotly_chart(fig, width="stretch", key=self._k(f"taqs_sochma_{x}_{y}"))
            if pd.notna(r):
                kuch = "juda kuchli" if abs(r) >= 0.8 else "kuchli" if abs(r) >= 0.6 else "o'rtacha" if abs(r) >= 0.3 else "kuchsiz"
                st.caption(f"Pirson korrelyatsiyasi: **r = {r:.3f}** — {kuch} {'musbat' if r > 0 else 'manfiy'} bog'liqlik.")

    # ----------------------------------------------------------------- xulosalar
    def _tab_xulosalar(self) -> None:
        st.markdown("##### 💡 Avtomatik topilgan xulosalar")
        for ikonka, matn in AqlliXulosalar(self.df, self.p, self.t).yaratish():
            st.markdown(f'<div class="insight"><div class="e">{ikonka}</div><div>{matn}</div></div>',
                        unsafe_allow_html=True)
        st.markdown("##### 🚨 Chetlashmalar (IQR usuli)")
        jadval = chetlashmalar_jadvali(self.df, self.p.raqamli)
        if jadval.empty:
            st.success("Sezilarli chetlashma topilmadi ✅")
        else:
            st.dataframe(jadval, width="stretch", hide_index=True)

    # --------------------------------------------------------------------- sifat
    def _tab_sifat(self) -> None:
        sifat = sifat_bahosi(self.asl)
        c = st.columns(4)
        c[0].metric("Umumiy ball", f"{sifat['ball']:.0f} / 100")
        c[1].metric("Yetishmagan qiymatlar", f"{sifat['yetishmagan']:.2f}%")
        c[2].metric("Takroriy qatorlar", f"{sifat['takror']:.2f}%")
        c[3].metric("Xotira hajmi", f"{self.asl.memory_usage(deep=True).sum() / 1024 ** 2:.1f} MB")

        if self.asl.isna().any().any():
            st.plotly_chart(GrafikFabrikasi.yetishmagan(self.asl), width="stretch", key=self._k("sifat_yetishmagan"))
        else:
            st.success("Yetishmayotgan qiymat yo'q ✅")

        rol: dict[str, str] = {}
        for nom, royxat in (("Raqamli", self.p.raqamli), ("Sana", self.p.sanali), ("Matn", self.p.matnli),
                            ("ID", self.p.id_ustunlar)):
            rol.update({u: nom for u in royxat})
        for u in self.p.kategorik:
            rol.setdefault(u, "Kategorik")
        tur = pd.DataFrame({
            "Ustun": self.asl.columns,
            "Aniqlangan rol": [rol.get(u, "Kategorik") for u in self.asl.columns],
            "dtype": [str(x) for x in self.asl.dtypes],
            "Noyob qiymatlar": [self.asl[u].nunique() for u in self.asl.columns],
            "Yetishmagan (%)": (self.asl.isna().mean() * 100).round(2).to_numpy(),
        })
        st.markdown("##### 🧬 Ustunlar profili")
        st.dataframe(tur, width="stretch", hide_index=True)
        if self.p.raqamli:
            st.markdown("##### 📋 Tavsifiy statistika")
            st.dataframe(self.df[self.p.raqamli].describe().T.round(2), width="stretch")

    # -------------------------------------------------------------------- jadval
    def _tab_jadval(self) -> None:
        st.caption(f"Ko'rsatilmoqda: {len(self.df):,} qator (filtrlar va kross-filtr qo'llangan).")
        st.dataframe(self.df, width="stretch", height=480)
        c1, c2, _ = st.columns([1, 1, 4])
        c1.download_button("⬇️ CSV yuklab olish", self.df.to_csv(index=False).encode("utf-8-sig"),
                           "tahlil_natijasi.csv", "text/csv", width="stretch")
        try:
            bufer = io.BytesIO()
            with pd.ExcelWriter(bufer, engine="openpyxl") as yozuvchi:
                self.df.to_excel(yozuvchi, index=False, sheet_name="Malumot")
            c2.download_button("⬇️ Excel yuklab olish", bufer.getvalue(), "tahlil_natijasi.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        except Exception:  # noqa: BLE001 - openpyxl o'rnatilmagan bo'lishi mumkin
            c2.caption("Excel uchun: pip install openpyxl")


def main() -> None:
    """Ilovaning kirish nuqtasi."""
    st.set_page_config(page_title=Sozlamalar.SAHIFA_NOMI, page_icon=Sozlamalar.IKONKA, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    xom, nom, prefiks = MalumotManbai().yuklash()
    df, profil = tayyorlash(xom)
    if df.empty:
        st.error("Fayl bo'sh ko'rinadi.")
        st.stop()

    tanlov = YonPanel(df, profil, prefiks).sozlamalar()
    filtrli = FiltrPaneli(df, profil, tanlov, prefiks).qollash()
    if filtrli.empty:
        st.warning("Tanlangan filtrlar bo'yicha ma'lumot topilmadi. Filtrlarni yumshatib ko'ring.")
        st.stop()

    # Kross-filtr: oldingi rerun'da grafikda bosilgan kategoriyalarni o'qiymiz
    qiymatlar = tanlangan_qiymatlar(kross_kalit(prefiks, tanlov.kategoriya)) if tanlov.kategoriya else []
    kross = filtrli
    if qiymatlar:
        kross = filtrli[filtrli[tanlov.kategoriya].astype(str).isin(qiymatlar)]
        if kross.empty:
            kross, qiymatlar = filtrli, []

    panel = Dashboard(df, filtrli, kross, profil, tanlov, nom, prefiks)
    panel._kross_faol = bool(qiymatlar)
    panel._kross_qiymatlar = qiymatlar
    panel.chizish()


if __name__ == "__main__":
    main()