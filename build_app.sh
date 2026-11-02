#!/bin/bash
# يبني تطبيق macOS مستقل: dist/محوّل الوسائط.app
set -e
# الأدوات تُشغَّل عبر python -m حتى يبقى السكربت يعمل لو تغيّر اسم مجلد المشروع أو مكانه
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  # يجب أن يكون بايثون Universal (Intel + Apple Silicon) — بايثون أدوات Xcode في /usr/bin/python3 كذلك
  "${PYTHON:-python3}" -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
fi
.venv/bin/python -m pip install -q -r requirements.txt pyinstaller

# أيقونة التطبيق
rm -rf build/icon.iconset && mkdir -p build/icon.iconset
.venv/bin/python app.py --export-icon build/icon_1024.png
for s in 16 32 128 256 512; do
  sips -z $s $s build/icon_1024.png --out build/icon.iconset/icon_${s}x${s}.png >/dev/null
  sips -z $((s*2)) $((s*2)) build/icon_1024.png --out build/icon.iconset/icon_${s}x${s}@2x.png >/dev/null
done
iconutil -c icns build/icon.iconset -o build/AppIcon.icns

# محرك FFmpeg للمعمارتين: Intel و Apple Silicon (M1–M5)، ليعمل التطبيق أصلياً بدون Rosetta.
# imageio-ffmpeg يختار النسخة المناسبة للجهاز تلقائياً وقت التشغيل.
FF_DIR=$(.venv/bin/python -c "import imageio_ffmpeg, os; print(os.path.join(os.path.dirname(imageio_ffmpeg.__file__), 'binaries'))")
FF_VER=$(.venv/bin/python -c "import imageio_ffmpeg; print(imageio_ffmpeg.__version__)")
fetch_ffmpeg() {  # $1 = منصة الحزمة في PyPI، $2 = اسم المعمارية في اسم الملف
  ls "$FF_DIR"/ffmpeg-macos-$2-* >/dev/null 2>&1 && return
  rm -rf "build/ff-$2" && mkdir -p "build/ff-$2"
  .venv/bin/python -m pip download -q "imageio-ffmpeg==$FF_VER" --platform "$1" --only-binary=:all: --no-deps -d "build/ff-$2"
  unzip -q -o "build/ff-$2"/*.whl "imageio_ffmpeg/binaries/ffmpeg-macos-$2-*" -d "build/ff-$2"
  cp "build/ff-$2"/imageio_ffmpeg/binaries/ffmpeg-macos-$2-* "$FF_DIR/"
  chmod +x "$FF_DIR"/ffmpeg-macos-$2-*
}
fetch_ffmpeg macosx_11_0_arm64 aarch64
fetch_ffmpeg macosx_10_9_x86_64 x86_64

# الاسم الداخلي إنجليزي لأن codesign يفشل في توقيع ملف تنفيذي باسم عربي،
# والاسم الظاهر للمستخدم (Dock والقوائم ومجلد التطبيق) يبقى عربياً
APP_NAME="محوّل الوسائط"
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed --log-level WARN \
  --name MediaConverter \
  --target-arch universal2 \
  --icon build/AppIcon.icns \
  --osx-bundle-identifier com.mediaconverterpro.app \
  --collect-data imageio_ffmpeg \
  --exclude-module tkinter \
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.Qt3DCore \
  --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtPdf \
  app.py 2>&1 | grep -v "signing the bundle\|sign the bundle manually\|replacing existing signature" || true

APP="dist/MediaConverter.app"
PLIST="$APP/Contents/Info.plist"
plist_set() {
  /usr/libexec/PlistBuddy -c "Set :$1 $2" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :$1 string $2" "$PLIST"
}
plist_set CFBundleName "$APP_NAME"
plist_set CFBundleDisplayName "$APP_NAME"
plist_set LSMinimumSystemVersion 13.0

# التوقيع من الداخل للخارج: كل framework، ثم الملف التنفيذي، ثم التطبيق كاملاً
xattr -cr "$APP"
find "$APP/Contents" -name "ffmpeg-macos-*" -type f -exec codesign --force -s - {} \; 2>/dev/null
find "$APP/Contents/Frameworks" -name "*.framework" -type d -prune -exec codesign --force -s - {} \; 2>/dev/null
codesign --force -s - "$APP/Contents/MacOS/MediaConverter" 2>/dev/null
codesign --force -s - "$APP" 2>/dev/null
codesign --verify --deep --strict "$APP"

# اسم مجلد التطبيق بالعربي (لا يؤثر على التوقيع) + نسخة مضغوطة جاهزة للإرسال
rm -rf "dist/$APP_NAME.app" "dist/$APP_NAME.zip" dist/MediaConverter build MediaConverter.spec
mv "$APP" "dist/$APP_NAME.app"
ditto -c -k --keepParent "dist/$APP_NAME.app" "dist/$APP_NAME.zip"

echo ""
echo "✓ تم البناء والتوقيع: dist/$APP_NAME.app"
echo "✓ نسخة للإرسال لجهاز ثاني: dist/$APP_NAME.zip"
