# uni-pdf

**PDF와 이미지를 오가는, 가장 안전한 방법.**

uni-pdf 는 PDF를 이미지로, 이미지를 PDF로 바꾸고 PDF 페이지를 정리하는 무료 프로그램입니다.
가장 큰 차이는 **보안**입니다 — 모든 변환이 **사용자 PC에서만** 이뤄지고, 파일을 인터넷으로
업로드하지 않습니다. (이 저장소의 소스를 보시면, 네트워크 코드가 한 줄도 없다는 걸 확인하실 수 있습니다.)

> A free, **offline** PDF utility: PDF ↔ JPG conversion and PDF page editing.
> Everything runs locally — your files are never uploaded.

---

## 기능

- **PDF → JPG** — 각 쪽을 이미지로 저장. `이름_1.jpg`, `이름_2.jpg` … 원본 해상도 유지.
- **JPG → PDF** — 여러 이미지를 하나의 PDF로 묶기.
- **PDF 편집** — 썸네일로 보며 순서 변경 · 삭제 · 다른 PDF와 합치기.

무설치 단일 실행 파일 · 광고 없음 · 데이터 수집 없음 · Windows / macOS.

## 다운로드

[Releases](../../releases) 에서 Windows(.exe) / macOS(.zip) 를 받으세요.

- **Windows**: 실행 시 "알 수 없는 게시자" SmartScreen 경고가 뜰 수 있습니다(무료 배포라
  코드서명 없음). "추가 정보 → 실행" 으로 진행하세요.
- **macOS**: 서명·공증되어 경고 없이 열립니다.

## 개발자 — 직접 빌드하기

빌드 방법은 [BUILD.md](BUILD.md) 참고. 요약:

```
pip install -r requirements.txt
python uni_pdf.py    # 실행
# Windows exe: pyinstaller --onefile --windowed --name uni-pdf-v1.0-windows --collect-all customtkinter --add-data "fonts;fonts" uni_pdf.py
```

## 라이선스

[LICENSE](LICENSE) 참고. **무료 사용 가능. 수정·재배포·판매는 금지**됩니다.
포함된 오픈소스(CustomTkinter, pypdfium2, Pillow, pypdf, Pretendard)는 각자의 라이선스를 따릅니다.

문의: uniflow.kr@gmail.com
