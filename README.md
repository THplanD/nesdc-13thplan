# nesdc-13thplan — automatic CSV download

ไฟล์ชุดนี้ไม่มี CSV แนบมา ต้องรัน GitHub Actions เพื่อดึงไฟล์จากเว็บไซต์ สศช. ก่อน

1. สร้าง GitHub repository ชื่อ `nesdc-13thplan` (Public)
2. อัปโหลด `index.html`, `sync_nesdc.py`, `README.md` และ `.github/workflows/sync-nesdc.yml` โดยคงเส้นทางตามนี้ **การอัปโหลดผ่านหน้าเว็บอาจไม่รักษาโฟลเดอร์ .github; ตรวจสอบให้ชัดเจน**
3. Settings → Actions → General → Workflow permissions → Read and write permissions (ถ้ามี)
4. Actions → Sync original NESDC milestone CSVs → Run workflow
5. ตรวจผลการรันว่าไฟล์ `csv/dashboard-data-milestone-N.csv` ถูกสร้างครบกี่หมุดหมาย
6. Settings → Pages → Deploy from a branch → main → /(root)
7. เปิด `https://USERNAME.github.io/nesdc-13thplan/`

รอบอัตโนมัติทุกวันเวลา 10:20 น. ไทย (อาจล่าช้าตามระบบ GitHub)

หมายเหตุ: การดาวน์โหลดผ่าน Playwright ยังไม่ได้ทดสอบสำเร็จกับเว็บไซต์ สศช. ในสภาพแวดล้อมนี้ หากไฟล์ยังไม่ปรากฏ ให้ดู Logs และ Debug screenshots ใน Actions; ปุ่มดาวน์โหลดหน้าเว็บจะใช้ได้เมื่อมี CSV จริงเท่านั้น และอาจต้องได้รับอนุญาตให้เผยแพร่ข้อมูลต้นทางซ้ำ
