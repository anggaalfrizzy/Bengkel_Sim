# Simulasi Antrian Bengkel (2 Montir)
Web simulasi kejadian diskrit (DES) untuk TA-05, Pemodelan dan Simulasi. Backend Python (Flask), mesin simulasi sama dengan notebook `.ipynb`.

## Jalankan lokal
    pip install -r requirements.txt
    python app.py        # http://localhost:5000

## Deploy ke Railway
1. Push folder ini ke GitHub.
2. Railway: New Project, Deploy from GitHub repo. `Procfile` dan `requirements.txt` terdeteksi otomatis.
3. (Opsional) Variables: `STUDENT_NAME`, `STUDENT_NIM` untuk footer.
4. Settings, Networking, Generate Domain.
