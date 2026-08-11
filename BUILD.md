# uni-pdf 빌드·실행 안내

## 개발/테스트 (맥·윈도우 공통)
```
pip install -r requirements.txt
python uni_pdf.py
```
라이브러리가 전부 크로스플랫폼이라 맥에서도 GUI가 뜨고 3기능 다 동작한다(테스트용).

## 배포용 단일 exe 빌드 — 🔴 Windows 에서만
PyInstaller 는 크로스컴파일이 안 된다. **맥에서 빌드하면 맥 실행파일**이 나온다.
최종 `.exe` 는 **집PC(Windows)**에서 만든다.

```
pip install -r requirements.txt
python -m PyInstaller --onefile --windowed --name uni-pdf-v1.0-windows --icon uni-pdf.ico --collect-all customtkinter --add-data "fonts;fonts" uni_pdf.py
```
- `--onefile` : 단일 exe (폴더형 onedir 안 씀 — 사용자 오용 방지, 확정)
- `--windowed` : 실행 시 검은 콘솔창 안 뜨게
- `--collect-all customtkinter` : CTk 테마 json 등 데이터 파일 동봉 (없으면 실행 시 크래시)
- `--add-data "fonts;fonts"` : Pretendard 폰트 동봉 (**Windows 는 `;`**, macOS/Linux 는 `:`)
- 결과물: `dist/uni-pdf-v1.0-windows.exe` (PDFium+폰트 포함, 40~70MB)

아이콘을 넣으려면: `--icon uni-pdf.ico` 추가 (선택).

## 배포용 macOS 앱 — 🍎 서명 + 공증 (경고 없음)
본인 Apple Developer 유료 계정의 **Developer ID Application** 인증서로 공증하면
**맥 사용자가 경고 없이 더블클릭 실행**한다.

**최초 1회만:**
1. 개인 서명 값을 `build_mac.local.sh` (git 제외)에 넣는다:
   ```
   export UNIPDF_SIGN_IDENTITY="Developer ID Application: YOUR NAME (TEAMID)"
   export UNIPDF_APPLE_ID="you@example.com"
   export UNIPDF_TEAM_ID="TEAMID"
   export UNIPDF_NOTARY_PROFILE="uni-pdf-notary"
   ```
2. 앱 전용 암호 발급: appleid.apple.com → 로그인 및 보안 → 앱 암호 → 생성
3. keychain 프로필에 저장 (암호는 파일에 안 박음):
   ```
   xcrun notarytool store-credentials "uni-pdf-notary" \
     --apple-id "$UNIPDF_APPLE_ID" --team-id "$UNIPDF_TEAM_ID" --password <앱전용암호>
   ```

**이후엔 한 방:**
```
./build_mac.sh
```
→ 빌드 → 서명(hardened runtime + `entitlements.plist`) → 공증 제출 → staple →
   `dist/uni-pdf-mac.zip` 생성. **이 zip을 배포**한다.

## 배포 시 알아둘 것 (OS 별로 다름)
- **macOS**: 위 공증까지 하면 경고 없음. ✅ 안내 문구 불필요.
- **Windows**: 별도 유료 코드서명 인증서가 없어 **SmartScreen 경고**가 뜬다(정상).
  → 소개 페이지에 "무료 배포를 위해 코드서명을 뺐고, 이 경고는 정상. 추가 정보 → 실행"
  안내 문구를 넣는다(계획). Apple 계정으로는 Windows 서명 불가.
- **백신 오탐**: Windows onefile exe 는 백신(알약·V3·Defender)이 종종 오탐. 배포 전
  VirusTotal 확인 권장.

## 파일
- `uni_pdf.py` — 본체 (tkinter GUI + 3기능)
- `requirements.txt` — 의존성
- `entitlements.plist` — macOS hardened runtime 권한 (공증용)
- `build_mac.sh` — macOS 빌드+서명+공증+staple 자동화
- `README.md` — 기획·결정·라이선스 근거
- `BUILD.md` — 이 문서
