"""Mesin simulasi kejadian diskrit (sama dengan notebook TA5)."""
import numpy as np
import pandas as pd


def simulasi_bengkel(num_mobil=10, iat=None, t_daftar=None, t_servis=None, t_bayar=None,
                     jumlah_montir=2, seed=42,
                     mean_iat=10, mean_daftar=2, mean_servis=20, std_servis=5, mean_bayar=3,
                     prioritas_kasir=True, verbose=True):
    """
    Mode MANUAL : isi iat (len = num_mobil-1), t_daftar, t_servis, t_bayar (len = num_mobil)
    Mode ACAK   : biarkan None, data dibangkitkan dari distribusi (seed untuk reproduksibilitas)
    """
    # ---------- 1. INISIALISASI ----------
    rng = np.random.default_rng(seed)
    if iat is None:
        iat = rng.exponential(mean_iat, num_mobil - 1)
    if t_daftar is None:
        t_daftar = rng.exponential(mean_daftar, num_mobil)
    if t_servis is None:
        t_servis = rng.normal(mean_servis, std_servis, num_mobil)
    if t_bayar is None:
        t_bayar = rng.exponential(mean_bayar, num_mobil)

    # data per mobil (indeks 1..N); minimal 0.1 supaya tidak negatif/nol
    daftar = {i + 1: max(0.1, float(t_daftar[i])) for i in range(num_mobil)}
    servis = {i + 1: max(1.0, float(t_servis[i])) for i in range(num_mobil)}
    bayar  = {i + 1: max(0.1, float(t_bayar[i]))  for i in range(num_mobil)}

    clock = 0.0
    resepsionis = None                    # None = IDLE, atau (id_mobil, "DAFTAR"/"BAYAR")
    montir = [None] * jumlah_montir       # None = IDLE, atau id_mobil
    antrian_daftar, ruang_tunggu, antrian_kasir = [], [], []
    event_calendar = []                   # [waktu, urutan, tipe, id_mobil, idx_montir]
    seq = 0

    # statistik
    t_datang, t_masuk_rt, t_masuk_kasir, t_keluar = {}, {}, {}, {}
    wait_daftar, wait_montir, wait_kasir = {}, {}, {}
    busy_resepsionis = 0.0
    busy_montir = [0.0] * jumlah_montir
    area = {"daftar": 0.0, "tunggu": 0.0, "kasir": 0.0}
    max_q = {"daftar": 0, "tunggu": 0, "kasir": 0}
    log, riwayat_antrian = [], []

    def jadwalkan(waktu, tipe, mobil, idx=None):
        nonlocal seq
        seq += 1
        event_calendar.append([waktu, seq, tipe, mobil, idx])
        event_calendar.sort()

    # jadwalkan semua kedatangan (kedatangan pertama di clock 0)
    t = 0.0
    t_datang[1] = 0.0
    jadwalkan(0.0, "ARRIVAL", 1)
    for i in range(num_mobil - 1):
        t += float(iat[i])
        t_datang[i + 2] = t
        jadwalkan(t, "ARRIVAL", i + 2)

    # ---------- 3. EVENT HANDLER (fungsi pembantu) ----------
    def coba_mulai_resepsionis():
        nonlocal resepsionis
        if resepsionis is not None:
            return
        pilih = None
        if prioritas_kasir:
            if antrian_kasir: pilih = "BAYAR"
            elif antrian_daftar: pilih = "DAFTAR"
        else:
            if antrian_daftar: pilih = "DAFTAR"
            elif antrian_kasir: pilih = "BAYAR"
        if pilih == "DAFTAR":
            m = antrian_daftar.pop(0)
            wait_daftar[m] = clock - t_datang[m]
            resepsionis = (m, "DAFTAR")
            jadwalkan(clock + daftar[m], "END_REGISTRATION", m)
        elif pilih == "BAYAR":
            m = antrian_kasir.pop(0)
            wait_kasir[m] = clock - t_masuk_kasir[m]
            resepsionis = (m, "BAYAR")
            jadwalkan(clock + bayar[m], "END_PAYMENT", m)

    def coba_mulai_montir():
        while ruang_tunggu and None in montir:
            k = montir.index(None)          # montir bebas pertama
            m = ruang_tunggu.pop(0)
            wait_montir[m] = clock - t_masuk_rt[m]
            montir[k] = m
            jadwalkan(clock + servis[m], "END_REPAIR", m, k)

    def handle_arrival(m):
        antrian_daftar.append(m)
        coba_mulai_resepsionis()

    def handle_end_registration(m):
        nonlocal resepsionis, busy_resepsionis
        busy_resepsionis += daftar[m]
        resepsionis = None
        t_masuk_rt[m] = clock
        ruang_tunggu.append(m)              # cek montir via coba_mulai_montir (titik percabangan)
        coba_mulai_montir()
        coba_mulai_resepsionis()

    def handle_end_repair(m, k):
        busy_montir[k] += servis[m]
        montir[k] = None
        t_masuk_kasir[m] = clock
        antrian_kasir.append(m)
        coba_mulai_montir()
        coba_mulai_resepsionis()

    def handle_end_payment(m):
        nonlocal resepsionis, busy_resepsionis
        busy_resepsionis += bayar[m]
        resepsionis = None
        t_keluar[m] = clock
        coba_mulai_resepsionis()

    def status_resep():
        return "IDLE" if resepsionis is None else f"{resepsionis[1]} M{resepsionis[0]}"

    # ---------- 2. MAIN SIMULATION LOOP ----------
    while event_calendar:
        waktu, _, tipe, mobil, idx = event_calendar.pop(0)

        # akumulasi luas area panjang antrian (untuk rata-rata antrian)
        dt = waktu - clock
        area["daftar"] += len(antrian_daftar) * dt
        area["tunggu"] += len(ruang_tunggu) * dt
        area["kasir"]  += len(antrian_kasir) * dt
        clock = waktu

        if tipe == "ARRIVAL":            handle_arrival(mobil)
        elif tipe == "END_REGISTRATION": handle_end_registration(mobil)
        elif tipe == "END_REPAIR":       handle_end_repair(mobil, idx)
        elif tipe == "END_PAYMENT":      handle_end_payment(mobil)

        max_q["daftar"] = max(max_q["daftar"], len(antrian_daftar))
        max_q["tunggu"] = max(max_q["tunggu"], len(ruang_tunggu))
        max_q["kasir"]  = max(max_q["kasir"],  len(antrian_kasir))
        riwayat_antrian.append((clock, len(ruang_tunggu)))

        kalender = [f"{e[0]:.1f}:{e[2]}(M{e[3]})" for e in event_calendar[:3]]
        log.append({
            "Clock": round(clock, 2), "Event": tipe, "Mobil": mobil,
            "Antrian Daftar": len(antrian_daftar), "Ruang Tunggu": len(ruang_tunggu),
            "Antrian Kasir": len(antrian_kasir),
            **{f"Montir {j+1}": ("IDLE" if montir[j] is None else f"Mobil {montir[j]}") for j in range(jumlah_montir)},
            "Resepsionis": status_resep(),
            "Event Calendar (3 berikutnya)": ", ".join(kalender) if kalender else "-",
        })

    # ---------- 4. STATISTIK AKHIR ----------
    n = len(t_keluar)
    rata = lambda d: sum(d.values()) / len(d) if d else 0.0
    waktu_sistem = {m: t_keluar[m] - t_datang[m] for m in t_keluar}
    hasil = {
        "Total mobil selesai": n,
        "Total waktu simulasi (menit)": round(clock, 2),
        "Rata-rata tunggu antrian daftar (menit)": round(rata(wait_daftar), 2),
        "Rata-rata tunggu ruang tunggu / montir (menit)": round(rata(wait_montir), 2),
        "Maks tunggu ruang tunggu (menit)": round(max(wait_montir.values(), default=0), 2),
        "Rata-rata tunggu antrian kasir (menit)": round(rata(wait_kasir), 2),
        "Rata-rata waktu di bengkel (menit)": round(rata(waktu_sistem), 2),
        "Rata-rata panjang ruang tunggu": round(area["tunggu"] / clock, 3) if clock else 0,
        "Maks panjang ruang tunggu": max_q["tunggu"],
        "Utilisasi resepsionis (%)": round(100 * busy_resepsionis / clock, 2) if clock else 0,
        **{f"Utilisasi Montir {j+1} (%)": round(100 * busy_montir[j] / clock, 2) if clock else 0
           for j in range(jumlah_montir)},
    }
    detail = pd.DataFrame({
        "Datang": pd.Series(t_datang), "Tunggu Daftar": pd.Series(wait_daftar),
        "Durasi Daftar": pd.Series(daftar), "Tunggu Montir": pd.Series(wait_montir),
        "Durasi Servis": pd.Series(servis), "Tunggu Kasir": pd.Series(wait_kasir),
        "Durasi Bayar": pd.Series(bayar), "Keluar": pd.Series(t_keluar),
    }).round(2)
    detail.index.name = "Mobil"
    df_log = pd.DataFrame(log)

    if verbose:
        print("=== SIMULASI BENGKEL (%d montir, %d mobil) ===" % (jumlah_montir, num_mobil))
        print(df_log.to_string(index=False))
        print("\n=== HASIL SIMULASI ===")
        for k, v in hasil.items():
            print(f"{k:<50}: {v}")
    return df_log, detail, hasil, riwayat_antrian
