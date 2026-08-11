#!/bin/bash
# uni-pdf — macOS 빌드 + 서명 + 공증 + staple (경고 없는 배포용)
#
# ── 사전 준비 (최초 1회) ────────────────────────────────────────
# 1) 본인 Apple Developer 값을 build_mac.local.sh 에 넣는다 (git 제외 파일):
#      export UNIPDF_SIGN_IDENTITY="Developer ID Application: YOUR NAME (TEAMID)"
#      export UNIPDF_APPLE_ID="you@example.com"
#      export UNIPDF_TEAM_ID="TEAMID"
#      export UNIPDF_NOTARY_PROFILE="uni-pdf-notary"   # (선택, 기본값 동일)
# 2) 앱 전용 암호 발급: appleid.apple.com → 로그인 및 보안 → 앱 암호 → 생성
# 3) keychain 프로필에 저장 (암호는 여기 한 번만, 파일엔 안 박음):
#      xcrun notarytool store-credentials "uni-pdf-notary" \
#        --apple-id "$UNIPDF_APPLE_ID" --team-id "$UNIPDF_TEAM_ID" --password <앱전용암호>
# ── 이후엔 이 스크립트만 실행하면 끝 ────────────────────────────
set -e
cd "$(dirname "$0")"

# 개인 서명 정보는 git 제외 파일에서 (공개 리포에 실명·팀ID 노출 방지)
[ -f "./build_mac.local.sh" ] && source "./build_mac.local.sh"

APP="uni-pdf"
VER="$(grep -m1 'APP_VERSION' uni_pdf.py | sed 's/.*"\(.*\)".*/\1/')"   # uni_pdf.py 에서 버전 자동 추출
DIST="uni-pdf-v${VER}-macos"                                            # 배포 zip 이름 (OS·버전 표기)
IDENTITY="${UNIPDF_SIGN_IDENTITY:?build_mac.local.sh 에 UNIPDF_SIGN_IDENTITY 를 설정하세요 (사전 준비 1 참고)}"
PROFILE="${UNIPDF_NOTARY_PROFILE:-uni-pdf-notary}"

echo "① 빌드 (단일 .app)"
# `pyinstaller` 실행파일이 PATH 에 없을 수 있어(python.org 파이썬의 bin 미등록) 모듈로 호출한다.
python3 -m PyInstaller --onefile --windowed --name "$APP" \
  --icon uni-pdf.icns \
  --osx-entitlements-file entitlements.plist \
  --collect-all customtkinter \
  --add-data "fonts:fonts" \
  uni_pdf.py

echo "② 서명 (hardened runtime + entitlements)"
codesign --deep --force --timestamp --options runtime \
  --entitlements entitlements.plist \
  --sign "$IDENTITY" "dist/$APP.app"

echo "③ 공증용 zip"
ditto -c -k --keepParent "dist/$APP.app" "dist/$APP-notarize.zip"

echo "④ 공증 제출 (완료까지 대기)"
xcrun notarytool submit "dist/$APP-notarize.zip" \
  --keychain-profile "$PROFILE" --wait

echo "⑤ staple (공증 결과를 앱에 박기 → 오프라인에서도 통과)"
xcrun stapler staple "dist/$APP.app"

echo "⑥ 배포용 zip"
ditto -c -k --keepParent "dist/$APP.app" "dist/$DIST.zip"

echo "✅ 완료 → dist/$DIST.zip (이 파일을 배포). 사용자는 경고 없이 더블클릭 실행."
