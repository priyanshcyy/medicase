Put real, openly licensed images here BEFORE running `python seed.py`:
  real_images/xray/   chest/knee/spine X-rays  (.jpg .png .webp)
  real_images/scan/   MRI / CT / ultrasound     (.jpg .png .webp)
seed.py picks them at random and attaches them to the synthetic patients (resized to max 1024 px).
They are NOT those patients' own scans - the app labels them "public dataset sample".
Sources: NIH ChestX-ray14, Open-I (US National Library of Medicine), MedPix, TCIA.
Check each dataset's licence/terms yourself. Do not use credentialed sets (MIMIC-CXR, CheXpert) here: their terms forbid redistribution.
If these folders are empty, synthetic placeholder images are generated instead.
