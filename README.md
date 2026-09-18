# Aozora Reader

青空文庫テキストを読むためのミニマルなタイプライター風リーダーです。
Python + raylib (pyray) で実装されています。

## 特徴

- タイプライター風の1文字ずつ表示
- 日本語フォント対応（PixelMplus 10px / 12px）
- ページ分割表示
- 効果音（自動生成されるタイピング音）
- ゲームパッ対応
- 高速送り（長押し）

## ファイル構成

```
.
├── README.md
├── requirements.txt
├── reader.py
├── aozora_416.txt
└── fonts/
    ├── PixelMplus10-Regular.ttf
    └── PixelMplus12-Regular.ttf
```

## 依存関係

```
pyray
```

## インストール

```bash
pip install -r requirements.txt
```

## 実行

```bash
python reader.py
```

## 操作方法

### キーボード

| キー | 動作 |
|------|------|
| Z / SPACE | 進む / スキップ（長押しで高速送り） |
| X | 前ページ |
| ↓ | 次ページ（強制） |
| ↑ | 前ページ（強制） |
| F | フォントサイズ切り替え（10px / 12px） |
| R | 全体リセット |
| Q | 終了 |

### ゲームパッド（Xbox系レイアウト）

| ボタン | 動作 |
|--------|------|
| A | 進む / スキップ（長押しで高速送り） |
| B | 前ページ |
| X | フォントサイズ切り替え |
| Y | 全体リセット |
| DPAD ↑↓ | 強制ページ移動 |

## フォントについて

`fonts/` ディクトリに以下の2種類のフォントを配置してください。

- `PixelMplus10-Regular.ttf`
- `PixelMplus12-Regular.ttf`

[PixelMplus](https://github.com/itouhiro/pixelfont) は itouhiro 氏によるフォントです。配布元のライセンスに従ってご利用ください。

## テキストファイル

`aozora_416.txt` を同じディレクトリに置くと読み込みます。ファイル名は `reader.py` 内の `FILE_PATH` で変更可能です。

## ビルド（配布用）

PyInstaller を使って単体実行ファイルにできます。

```bash
pip install pyinstaller
pyinstaller --onefile --windowed \
  --add-data "aozora_416.txt:." \
  --add-data "fonts:fonts" \
  --add-data "typing_click.wav:." \
  reader.py
```

## 注意

- 初回実行時に `typing_click.wav` が自動生成されます。
- フォントが見つからない場合はデフォルトフォントにフォールバックしますが、日本語は正しく表示されません。
