import os
from flask import Flask, render_template, request, jsonify
from engine import simulasi_bengkel

app = Flask(__name__)
app.json.sort_keys = False  # pertahankan urutan kolom tabel


def angka(teks, n, nama):
    try:
        v = [float(x) for x in str(teks).replace(";", ",").replace("\n", ",").split(",") if x.strip()]
    except ValueError:
        raise ValueError(f"{nama}: isi hanya angka, dipisah koma.")
    if len(v) != n:
        raise ValueError(f"{nama}: dibutuhkan {n} nilai, yang diisi {len(v)}.")
    if any(x < 0 for x in v):
        raise ValueError(f"{nama}: nilai tidak boleh negatif.")
    return v


def tabel_manual(detail):
    """Perhitungan manual per mobil: rantai waktu mulai/selesai tiap tahap."""
    rows, prev = [], None
    for mobil, r in detail.iterrows():
        md = r["Datang"] + r["Tunggu Daftar"]
        sd = md + r["Durasi Daftar"]
        ms = sd + r["Tunggu Montir"]
        ss = ms + r["Durasi Servis"]
        mb = ss + r["Tunggu Kasir"]
        rows.append({"Mobil": int(mobil), "IAT": "-" if prev is None else round(r["Datang"] - prev, 2),
                     "Datang": r["Datang"], "Mulai Daftar": round(md, 2), "Selesai Daftar": round(sd, 2),
                     "Tunggu Montir": r["Tunggu Montir"], "Mulai Servis": round(ms, 2), "Selesai Servis": round(ss, 2),
                     "Mulai Bayar": round(mb, 2), "Selesai Bayar": r["Keluar"],
                     "Waktu di Bengkel": round(r["Keluar"] - r["Datang"], 2)})
        prev = r["Datang"]
    return rows


@app.get("/")
def index():
    return render_template("index.html", nama=os.getenv("STUDENT_NAME", "Nama Mahasiswa"),
                           nim=os.getenv("STUDENT_NIM", "NIM"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/simulate")
def simulate():
    d = request.get_json(force=True, silent=True) or {}
    try:
        n, m = int(d.get("num_mobil", 7)), int(d.get("montir", 2))
        if not 2 <= n <= 200: raise ValueError("Jumlah mobil harus 2 sampai 200.")
        if not 1 <= m <= 5: raise ValueError("Jumlah montir harus 1 sampai 5.")
        if d.get("mode") == "manual":
            kw = dict(iat=angka(d.get("iat"), n - 1, "Antar-kedatangan"),
                      t_daftar=angka(d.get("t_daftar"), n, "Durasi pendaftaran"),
                      t_servis=angka(d.get("t_servis"), n, "Durasi perbaikan"),
                      t_bayar=angka(d.get("t_bayar"), n, "Durasi pembayaran"))
        else:
            kw = dict(seed=int(d.get("seed", 42)), mean_iat=float(d.get("mean_iat", 10)),
                      mean_daftar=float(d.get("mean_daftar", 2)), mean_servis=float(d.get("mean_servis", 20)),
                      std_servis=float(d.get("std_servis", 5)), mean_bayar=float(d.get("mean_bayar", 3)))
        log, detail, hasil, riw = simulasi_bengkel(num_mobil=n, jumlah_montir=m, verbose=False,
                                                   prioritas_kasir=bool(d.get("prioritas_kasir", True)), **kw)
    except (ValueError, TypeError) as e:
        return jsonify(error=str(e)), 400
    return jsonify(log=log.to_dict("records"), detail=detail.reset_index().to_dict("records"),
                   manual=tabel_manual(detail), hasil=hasil, antrian=riw)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
