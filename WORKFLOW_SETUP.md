# إعداد GitHub Actions Workflow

بسبب قيود صلاحيات GitHub App، يجب إضافة ملف workflow يدوياً. اتبع الخطوات التالية:

## الطريقة 1: عبر واجهة GitHub (الأسهل)

1. افتح المستودع على GitHub: https://github.com/MoainAlabbasi/generator-manager
2. اذهب إلى تبويب **Actions**
3. اضغط على **"set up a workflow yourself"** أو **"New workflow"**
4. احذف المحتوى الافتراضي والصق الكود التالي:

```yaml
name: Build Android APK

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  build-apk:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
      
      - name: Setup Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flet
      
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: stable
      
      - name: Build APK
        run: |
          flet build apk --verbose
      
      - name: Upload APK Artifact
        uses: actions/upload-artifact@v4
        with:
          name: generator-manager-apk
          path: build/apk/app-release.apk
          if-no-files-found: error
```

5. احفظ الملف باسم `build_apk.yml`
6. اضغط **Commit changes**

## الطريقة 2: عبر سطر الأوامر (إذا كانت لديك الصلاحيات)

إذا كنت تستخدم Personal Access Token بدلاً من GitHub App:

```bash
cd generator-manager
git pull
git add .github/workflows/build_apk.yml
git commit -m "Add GitHub Actions workflow for APK build"
git push
```

## التحقق من نجاح الإعداد

1. بعد إضافة الملف، اذهب إلى تبويب **Actions** في المستودع
2. يجب أن ترى workflow بعنوان "Build Android APK"
3. سيتم تشغيله تلقائياً عند كل push إلى فرع main
4. يمكنك أيضاً تشغيله يدوياً من خلال زر "Run workflow"

## تحميل APK المبني

1. بعد نجاح تشغيل الـ workflow، اذهب إلى صفحة الـ workflow run
2. ستجد في الأسفل قسم **Artifacts**
3. اضغط على **generator-manager-apk** لتحميل ملف APK

## ملاحظات

- البناء الأول قد يستغرق 10-15 دقيقة بسبب تحميل Flutter SDK
- البناءات اللاحقة ستكون أسرع بفضل التخزين المؤقت
- ملف APK الناتج سيكون موقعاً ذاتياً (self-signed) ويحتاج إلى تفعيل "تثبيت من مصادر غير معروفة" على Android
