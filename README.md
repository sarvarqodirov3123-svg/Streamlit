# 📊 Universal Analitika Paneli

Istalgan jadval ko'rinishidagi ma'lumot (CSV, Excel, JSON, Parquet) faylini yuklab, bir necha soniyada **interaktiv analitika paneli** olish uchun [Streamlit](https://streamlit.io) asosida yozilgan ilova.

Ilova ustunlar turini (raqam, sana, kategoriya, matn, ID) **avtomatik aniqlaydi**, shuning uchun har bir yangi fayl uchun qo'lda sozlash shart emas. Fayl yuklanmasa, ilova demo savdo ma'lumoti bilan ishga tushadi.

---

## ✨ Asosiy imkoniyatlar

- **Ko'p formatli yuklash**: `csv`, `tsv`, `txt`, `xlsx`, `xlsm`, `xls`, `json`, `parquet`
- **Avtomatik tur aniqlash**: matn ko'rinishidagi raqamlar (`"1 250,50"`) va sanalar haqiqiy turga o'tkaziladi
- **Kodlashni aniqlash**: CSV uchun `utf-8-sig`, `utf-8`, `cp1251`, `latin-1` ketma-ket sinab ko'riladi; ajratuvchi (`,` `;` tab) avtomatik topiladi
- **6 ta KPI karta**: tanlangan qatorlar, asosiy ko'rsatkich (sparkline va o'zgarish foizi bilan), davr o'rtachasi, eng yuqori davr, yetakchi kategoriya, ma'lumot sifati
- **Kross-filtr**: o'ng tomondagi grafikda ustunni bossangiz, butun panel shu kategoriyaga moslashadi (bir nechtasini tanlash uchun `Shift`)
- **Dinamik filtrlar**: sana oralig'i, kategorik va raqamli filtrlar
- **Aqlli xulosalar**: ma'lumotga qarab avtomatik matnli tahlil (yetakchi kategoriya, trend, Pareto, eng faol hafta kuni, korrelyatsiya, chetlashmalar, yetishmovchilik, assimetriya)
- **Ma'lumot sifati bahosi** (0–100) va chetlashmalarni IQR usulida topish
- **Natijani yuklab olish**: filtrlangan jadvalni CSV yoki Excel ko'rinishida

---

## 🗂️ Panel bo'limlari (yorliqlar)

| Yorliq | Mazmuni |
|---|---|
| 📈 **Vaqt tahlili** | Trend chizig'i, harakatlanuvchi o'rtacha, anomaliyalar (z-score > 2.5), chiziqli prognoz (12 davrgacha), davrdan davrga o'zgarish, hafta kunlari va hafta kuni × oy issiqlik xaritasi |
| 🧩 **Kategoriyalar** | Pareto (80/20) diagrammasi, donut, treemap, ikki kategoriya kesishmasi (pivot issiqlik xaritasi), box-plot |
| 🔬 **Taqsimot va bog'liqlik** | Gistogramma, asosiy statistikalar, korrelyatsiya matritsasi, scatter grafik (rang va o'lcham bilan) va Pirson `r` koeffitsienti |
| 💡 **Aqlli xulosalar** | Avtomatik topilgan xulosalar va chetlashmalar jadvali |
| 🧪 **Ma'lumot sifati** | Umumiy ball, yetishmagan qiymatlar, takroriy qatorlar, xotira hajmi, ustunlar profili, tavsifiy statistika |
| 🗂️ **Jadval** | Filtrlangan ma'lumot jadvali va yuklab olish tugmalari |

---

## 🚀 O'rnatish va ishga tushirish

**Talablar:** Python 3.9+ (kod `from __future__ import annotations` ishlatadi)

```bash
# 1. (ixtiyoriy) virtual muhit yaratish
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. kutubxonalarni o'rnatish
pip install streamlit pandas numpy plotly openpyxl

# 3. ilovani ishga tushirish
streamlit run main.py
```

Brauzerda odatda `http://localhost:8501` manzilida ochiladi.

### Kutubxonalar

| Kutubxona | Nima uchun kerak |
|---|---|
| `streamlit` | Veb-interfeys. Kod `width="stretch"` parametrini ishlatadi, shuning uchun **yangi versiya** tavsiya etiladi (`pip install -U streamlit`) |
| `pandas`, `numpy` | Ma'lumotni qayta ishlash va hisob-kitoblar |
| `plotly` | Barcha interaktiv grafiklar |
| `openpyxl` | `.xlsx` / `.xlsm` fayllarni o'qish va Excel ga yuklab olish |
| `xlrd` | *(ixtiyoriy)* eski `.xls` fayllarni o'qish uchun |
| `pyarrow` | *(ixtiyoriy)* `.parquet` fayllarni o'qish uchun |

---

## 🧭 Foydalanish

1. Chap paneldagi **📂 Ma'lumot manbai** bo'limidan fayl tanlang (yoki demo bilan davom eting). Excel faylda bir nechta varaq bo'lsa, varaq tanlash chiqadi.
2. **⚙️ Tahlil sozlamalari** da quyidagilarni tanlang:
   - **Asosiy ko'rsatkich**: raqamli ustun (`tushum`, `sotuv`, `summa`, `price`, `profit` kabi nomlar avtomatik tanlanadi)
   - **Agregatsiya turi**: Yig'indi, O'rtacha, Medyana, Soni, Maksimum, Minimum
   - **Sana ustuni va davr**: Kunlik, Haftalik, Oylik, Choraklik, Yillik (sana oralig'iga qarab standart davr tanlanadi)
   - **Asosiy kategoriya** va **Top-N** (3–30)
3. **🎛️ Filtrlar** orqali ma'lumotni toraytiring.
4. Grafikdagi ustunni bosib, kross-filtrni yoqing. **✖ Tozalash** tugmasi bilan qaytarasiz.
5. Kerakli yorliqlarni ko'rib chiqing va natijani **🗂️ Jadval** yorlig'idan yuklab oling.

---

## 🧠 Ustun turlari qanday aniqlanadi

| Tur | Qoida |
|---|---|
| **Raqamli** | Matndagi qiymatlarning kamida 95% i songa aylansa (probel olib tashlanadi, `,` → `.`) |
| **Sana** | Namunaning 80% idan ortig'ida `- / . :` belgilari bo'lsa va 90% i sanaga aylansa |
| **ID** | Butun sonli, barcha qiymatlari noyob va 20 tadan ko'p bo'lgan ustun |
| **Kategorik** | Matnli ustun, noyob qiymatlari ≤ 50; yoki raqamli ustun, noyob qiymatlari ≤ 12 |
| **Matnli** | Noyob qiymatlari 50 tadan ko'p bo'lgan matnli ustun |

Bo'sh ustunlar va bo'sh qatorlar, takroriy ustun nomlari avtomatik olib tashlanadi.

---

## 🏗️ Kod tuzilishi (`main.py`)

| Bo'lim | Tarkibi |
|---|---|
| **1. Sozlamalar** | `Sozlamalar` sinfi: ranglar, gradientlar, agregatsiya funksiyalari, davrlar, formatlar |
| **2. Yordamchi funksiyalar** | `qisqa_raqam`, `sparkline_svg`, `agregatsiya`, `skalyar`, `vaqt_qatori`, `sifat_bahosi`, `chetlashmalar_jadvali` |
| **3. Ma'lumot** | `demo_malumot`, `faylni_oqish`, `excel_varaqlari`, `tayyorlash` va `Profil` dataclass (hammasi `st.cache_data` bilan keshlangan) |
| **4. Yon panel** | `MalumotManbai` (yuklash), `YonPanel` (global tanlovlar), `FiltrPaneli` (filtrlar), `Tanlovlar` dataclass |
| **5. Kross-filtr** | `kross_kalit`, `tanlangan_qiymatlar`, grafikdagi tanlovni `st.session_state` orqali o'qish |
| **6. Aqlli xulosalar** | `AqlliXulosalar` sinfi, har bir xulosa alohida metod; biri xato bersa, qolganlari ishlayveradi |
| **7. Grafiklar** | `GrafikFabrikasi`, Plotly grafiklarini yaratuvchi statik metodlar (yagona uslub `bezash` da) |
| **8. Interfeys** | `CSS`, `kpi_karta`, `Dashboard` (KPI, yorliqlar), `main()` kirish nuqtasi |

**Ish tartibi:** `MalumotManbai.yuklash()` → `tayyorlash()` → `YonPanel.sozlamalar()` → `FiltrPaneli.qollash()` → kross-filtr → `Dashboard.chizish()`

---

## 🛠️ Sozlash

Ko'p narsani faqat `Sozlamalar` sinfidan o'zgartirish mumkin:

- `SAHIFA_NOMI`, `IKONKA`: sarlavha va ikonka
- `RANG_ASOSIY`, `PALITRA`, `GRADIENTLAR`: ranglar
- `FUNKSIYALAR`, `DAVRLAR`: agregatsiya turlari va davrlar
- `MAX_KATEGORIYA`: matnli ustun kategorik hisoblanishi uchun maksimal noyob qiymatlar soni (standart: 50)
- `KALIT_SOZLAR`: asosiy ko'rsatkich sifatida avtomatik tanlanadigan ustun nomlari
- `QOLLANADIGAN_FORMATLAR`: yuklanadigan fayl turlari

---

## ⚠️ Cheklovlar

- Scatter grafik 5 000 tadan ko'p nuqtada tasodifiy namuna oladi
- Korrelyatsiya matritsasi dastlabki 25 ta raqamli ustun bilan cheklangan
- Prognoz oddiy **chiziqli regressiya**ga asoslangan, jiddiy prognozlash uchun mo'ljallanmagan
- Juda katta fayllar to'liq xotiraga o'qiladi
- Chetlashmalar IQR usulida topiladi va kamida 8 ta qiymat talab qilinadi

---

## 🎲 Demo ma'lumot

Fayl yuklanmasa, 4 000 qatorli sun'iy savdo ma'lumoti (2024–2025) ishlatiladi. Ustunlari: `Buyurtma_ID`, `Sana`, `Viloyat`, `Kategoriya`, `Mijoz_turi`, `Miqdor`, `Narx`, `Chegirma_%`, `Tushum`, `Foyda`, `Baho`. Tushumga mavsumiylik, o'sish trendi va ataylab bir nechta chetlashma qo'shilgan.
