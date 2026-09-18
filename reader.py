from pyray import *
import os
import wave
import struct
import math
import random

# ===== 設定 =====
SCREEN_W = 256
SCREEN_H = 256
FILE_PATH = "aozora_416.txt"
FONT_PATH_10 = "fonts/PixelMplus10-Regular.ttf"
FONT_PATH_12 = "fonts/PixelMplus12-Regular.ttf"

TEXT_AREA_X = 16
TEXT_AREA_Y = 16
TEXT_AREA_W = 220
FOOTER_H = 20

COLOR_BG      = Color(0, 0, 0, 255)
COLOR_BOX     = Color(29, 43, 83, 255)
COLOR_BORDER  = Color(255, 241, 232, 255)
COLOR_TEXT    = Color(255, 241, 232, 255)
COLOR_DEBUG   = Color(180, 180, 180, 255)
COLOR_WARN    = Color(255, 80, 80, 255)
COLOR_OVERLAY = Color(0, 0, 0, 200)
COLOR_ACCENT  = Color(255, 204, 0, 255)
COLOR_ARROW   = Color(200, 200, 200, 255)
COLOR_FAST    = Color(100, 255, 100, 255)


# ===================================================================
# SoundManager
# ===================================================================
class SoundManager:
    def __init__(self):
        self.audio_ready = False
        self.talk_sound = None
        self.sound_cooldown = 0
        self._init_audio()

    def _init_audio(self):
        try:
            init_audio_device()
            self._generate_talk_sound("talk_blip.wav")
            self.talk_sound = load_sound("talk_blip.wav")
            self.audio_ready = True
            print("[INFO] Audio initialized.")
        except Exception as e:
            print(f"[WARN] Audio init failed: {e}")
            self.audio_ready = False

    def _generate_talk_sound(self, path: str):
        """
        ファミコン風テキスト送り音（ポートピア/ドラクエ系）
        短い方形波 + 急減衰 + わずかな音程下げで「ピポッ」感を出す
        """
        sample_rate = 44100
        duration = 0.025          # 25ms とても短い
        base_freq = 1400          # 基本周波数（高めの「ピ」）
        bend_amount = 600         # 減衰中に下がる周波数量
        samples = int(sample_rate * duration)

        with wave.open(path, 'w') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            for i in range(samples):
                t = i / sample_rate
                progress = t / duration

                # 周波数を少し下げる（「ピ」→「ポ」感）
                freq = base_freq - (bend_amount * progress)

                # 方形波（square wave）
                phase = (t * freq) % 1.0
                square = 1.0 if phase < 0.5 else -1.0

                # 急激な減衰（最初だけ音が出てすぐ消える）
                envelope = math.exp(-t * 180)

                # わずかなノイズを混ぜてファミコンらしさを出す（0.05程度）
                noise = (random.random() * 2 - 1) * 0.05 * envelope

                val = square * envelope * 0.5 + noise
                val = max(-1.0, min(1.0, val))
                w.writeframes(struct.pack('<h', int(val * 32767)))

    def play_talk(self):
        if self.audio_ready and self.sound_cooldown <= 0 and is_sound_ready(self.talk_sound):
            play_sound(self.talk_sound)
            self.sound_cooldown = 2

    def update(self):
        if self.sound_cooldown > 0:
            self.sound_cooldown -= 1

    def cleanup(self):
        if self.audio_ready:
            if is_sound_ready(self.talk_sound):
                unload_sound(self.talk_sound)
            close_audio_device()


# ===================================================================
# InputManager
# ===================================================================
class InputManager:
    def __init__(self):
        self.gamepad_id = 0
        self.gamepad_available = False
        self.hold_timer = 0
        self.repeat_delay = 30
        self.fast_mode = False

    def update(self, can_fast_forward: bool):
        self.gamepad_available = is_gamepad_available(self.gamepad_id)
        if can_fast_forward and self.is_advance_held():
            self.hold_timer += 1
            if self.hold_timer > self.repeat_delay:
                self.fast_mode = True
        else:
            self.hold_timer = 0
            self.fast_mode = False

    def is_advance_pressed(self):
        if is_key_pressed(KEY_Z) or is_key_pressed(KEY_SPACE):
            return True
        if self.gamepad_available and is_gamepad_button_pressed(self.gamepad_id, GAMEPAD_BUTTON_RIGHT_FACE_DOWN):
            return True
        return False

    def is_back_pressed(self):
        if is_key_pressed(KEY_X):
            return True
        if self.gamepad_available and is_gamepad_button_pressed(self.gamepad_id, GAMEPAD_BUTTON_RIGHT_FACE_RIGHT):
            return True
        return False

    def is_next_forced(self):
        if is_key_pressed(KEY_DOWN):
            return True
        if self.gamepad_available and is_gamepad_button_pressed(self.gamepad_id, GAMEPAD_BUTTON_LEFT_FACE_DOWN):
            return True
        return False

    def is_prev_forced(self):
        if is_key_pressed(KEY_UP):
            return True
        if self.gamepad_available and is_gamepad_button_pressed(self.gamepad_id, GAMEPAD_BUTTON_LEFT_FACE_UP):
            return True
        return False

    def is_font_toggle_pressed(self):
        if is_key_pressed(KEY_F):
            return True
        if self.gamepad_available and is_gamepad_button_pressed(self.gamepad_id, GAMEPAD_BUTTON_RIGHT_FACE_LEFT):
            return True
        return False

    def is_reset_pressed(self):
        if is_key_pressed(KEY_R):
            return True
        if self.gamepad_available and is_gamepad_button_pressed(self.gamepad_id, GAMEPAD_BUTTON_RIGHT_FACE_UP):
            return True
        return False

    def is_quit_pressed(self):
        return is_key_pressed(KEY_Q)

    def is_advance_held(self):
        if is_key_down(KEY_Z) or is_key_down(KEY_SPACE):
            return True
        if self.gamepad_available and is_gamepad_button_down(self.gamepad_id, GAMEPAD_BUTTON_RIGHT_FACE_DOWN):
            return True
        return False


# ===================================================================
# App
# ===================================================================
class App:
    def __init__(self):
        init_window(SCREEN_W, SCREEN_H, "Aozora Reader")
        set_target_fps(60)
        self.should_quit = False
        self.font_missing = False
        self.using_custom_font = False

        self.sound = SoundManager()
        self.input = InputManager()

        self.paragraphs = self.load_paragraphs(FILE_PATH)
        self.full_text = "\n".join(self.paragraphs)

        self.font_size = 12
        self.font_paths = {10: FONT_PATH_10, 12: FONT_PATH_12}

        self.setup_font_and_layout(12)

        self.state = "reading"
        self.timer = 0
        self.char_interval = 2
        self.page_cooldown = 0
        self.blink_timer = 0

    def setup_font_and_layout(self, size: int):
        if self.using_custom_font and hasattr(self, 'font') and self.font is not None:
            try:
                unload_font(self.font)
            except Exception as e:
                print(f"[WARN] Font unload failed: {e}")
            self.using_custom_font = False

        self.font_size = size
        self.font_size_f = float(size)
        self.font_spacing = 1.0
        self.line_height = size + 4
        self.max_lines_per_page = (SCREEN_H - FOOTER_H - TEXT_AREA_Y) // self.line_height

        font_path = self.font_paths.get(size, FONT_PATH_12)
        self.font = self.load_japanese_font(font_path, size)

        self.wrapped_lines, self.line_counts = self.build_wrapped_lines(self.full_text, TEXT_AREA_W)
        self.pages = self.build_pages()

        old_page = getattr(self, 'current_page', 0)
        self.page_revealed = [0] * len(self.pages)
        self.current_page = min(old_page, len(self.pages) - 1)
        if self.current_page < 0:
            self.current_page = 0

    def load_japanese_font(self, path, size):
        if not os.path.exists(path):
            self.font_missing = True
            print(f"[WARN] Font not found: {path}")
            return get_font_default()

        try:
            unique_chars = sorted({c for c in self.full_text if ord(c) >= 32})
            codepoints = [ord(c) for c in unique_chars]
            font = load_font_ex(path, size, codepoints, len(codepoints))
            glyph_count = getattr(font, "glyphCount", getattr(font, "charsCount", "?"))
            print(f"[INFO] Loaded font: {path} @ {size}px ({glyph_count} glyphs)")
            self.using_custom_font = True
            return font
        except Exception as e:
            print(f"[ERROR] Font load failed: {e}")
            self.font_missing = True
            return get_font_default()

    def load_paragraphs(self, path):
        if not os.path.exists(path):
            return ["（ファイルが見つかりません）", "", "ここにテキストが表示されます。"]
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()

    def measure(self, text: str) -> float:
        if not text:
            return 0.0
        return measure_text_ex(self.font, text, self.font_size_f, self.font_spacing).x

    def wrap_paragraph(self, para: str, max_width: float):
        if not para:
            return [""]
        lines = []
        current = ""
        for ch in para:
            test = current + ch
            if self.measure(test) > max_width and current:
                lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def build_wrapped_lines(self, text: str, max_width: float):
        lines = []
        counts = []
        i = 0
        n = len(text)
        while i < n:
            start = i
            while i < n and text[i] != '\n':
                i += 1
            para = text[start:i]
            visual = self.wrap_paragraph(para, max_width)
            for vline in visual:
                lines.append(vline)
                counts.append(len(vline))
            if i < n and text[i] == '\n':
                if para == "":
                    lines.append("")
                    counts.append(1)
                else:
                    counts[-1] += 1
                i += 1
        return lines, counts

    def build_pages(self):
        pages = []
        start = 0
        total_lines = len(self.wrapped_lines)
        while start < total_lines:
            end = min(start + self.max_lines_per_page, total_lines)
            page_total = sum(self.line_counts[start:end])
            pages.append({
                'start': start,
                'end': end,
                'total': page_total,
            })
            start = end
        return pages

    def reset_all(self):
        self.current_page = 0
        self.page_revealed = [0] * len(self.pages)
        self.state = "reading"

    def toggle_font_size(self):
        new_size = 10 if self.font_size == 12 else 12
        print(f"[INFO] Switching font size to {new_size}px")
        self.setup_font_and_layout(new_size)

    def update(self):
        if window_should_close():
            self.should_quit = True
            return

        self.sound.update()
        self.input.update(self.state == "reading")
        self.blink_timer += 1

        if self.input.is_quit_pressed():
            self.should_quit = True
            return

        if self.page_cooldown > 0:
            self.page_cooldown -= 1
            return

        if self.state == "finished":
            if self.input.is_advance_pressed() or self.input.is_reset_pressed():
                self.reset_all()
            return

        page = self.pages[self.current_page]
        revealed = self.page_revealed[self.current_page]

        if revealed < page['total']:
            if self.input.fast_mode:
                self.page_revealed[self.current_page] += 1
                if self.page_revealed[self.current_page] % 4 == 0:
                    self.sound.play_talk()
            else:
                self.timer += 1
                if self.timer >= self.char_interval:
                    self.timer = 0
                    self.page_revealed[self.current_page] += 1
                    self.sound.play_talk()

        if self.input.fast_mode and self.page_revealed[self.current_page] >= page['total']:
            self.page_revealed[self.current_page] = page['total']
            if self.current_page < len(self.pages) - 1:
                self.current_page += 1
                self.page_cooldown = 8
                return
            else:
                self.state = "finished"
                return

        if self.input.is_advance_pressed():
            if revealed < page['total']:
                self.page_revealed[self.current_page] = page['total']
            else:
                if self.current_page < len(self.pages) - 1:
                    self.current_page += 1
                    self.page_cooldown = 8
                else:
                    self.state = "finished"

        if self.input.is_back_pressed():
            if self.current_page > 0:
                self.current_page -= 1
                self.page_cooldown = 8

        if self.input.is_next_forced():
            if self.current_page < len(self.pages) - 1:
                self.current_page += 1
                self.page_cooldown = 8

        if self.input.is_prev_forced():
            if self.current_page > 0:
                self.current_page -= 1
                self.page_cooldown = 8

        if self.input.is_font_toggle_pressed():
            self.toggle_font_size()

        if self.input.is_reset_pressed():
            self.reset_all()

    def draw_text_wrapper(self, text: str, x: float, y: float, color: Color):
        draw_text_ex(self.font, text, Vector2(x, y), self.font_size_f, self.font_spacing, color)

    def draw(self):
        begin_drawing()
        clear_background(COLOR_BG)

        draw_rectangle(8, 8, 240, 240, COLOR_BOX)
        draw_rectangle_lines(8, 8, 240, 240, COLOR_BORDER)

        if self.font_missing:
            msg = "Font not found"
            self.draw_text_wrapper(msg, 16, 120, COLOR_WARN)

        if self.state == "finished":
            draw_rectangle(0, 0, SCREEN_W, SCREEN_H, COLOR_OVERLAY)
            msg1 = "----- 読了 -----"
            msg2 = "A / Z: 最初からやり直す"
            msg3 = "Q: 終了"
            w1 = self.measure(msg1)
            w2 = self.measure(msg2)
            w3 = self.measure(msg3)
            y_center = SCREEN_H // 2 - 30
            self.draw_text_wrapper(msg1, (SCREEN_W - w1) // 2, y_center, COLOR_ACCENT)
            self.draw_text_wrapper(msg2, (SCREEN_W - w2) // 2, y_center + 24, COLOR_TEXT)
            self.draw_text_wrapper(msg3, (SCREEN_W - w3) // 2, y_center + 44, COLOR_DEBUG)

        else:
            page = self.pages[self.current_page]
            start = page['start']
            end = page['end']
            revealed = self.page_revealed[self.current_page]

            y = TEXT_AREA_Y
            chars_shown = 0
            for idx in range(start, end):
                line = self.wrapped_lines[idx]
                count = self.line_counts[idx]

                if chars_shown + count <= revealed:
                    self.draw_text_wrapper(line, TEXT_AREA_X, y, COLOR_TEXT)
                    chars_shown += count
                elif chars_shown < revealed:
                    remain = revealed - chars_shown
                    partial = line[:remain]
                    self.draw_text_wrapper(partial, TEXT_AREA_X, y, COLOR_TEXT)
                    chars_shown += remain
                    break
                else:
                    break

                y += self.line_height
                if y > SCREEN_H - FOOTER_H:
                    break

            is_page_complete = revealed >= page['total']
            has_next_page = self.current_page < len(self.pages) - 1
            if is_page_complete and has_next_page:
                if (self.blink_timer // 30) % 2 == 0:
                    arrow = "▼"
                    aw = self.measure(arrow)
                    self.draw_text_wrapper(arrow, (SCREEN_W - aw) // 2, SCREEN_H - 34, COLOR_ARROW)

            if self.input.fast_mode:
                hint = "[A]高速送り中..."
                hint_color = COLOR_FAST
            else:
                hint = f"[A]進 [B]戻 [X]{self.font_size}px"
                hint_color = COLOR_DEBUG

            self.draw_text_wrapper(hint, 10, SCREEN_H - 18, hint_color)

            page_info = f"{self.current_page + 1} / {len(self.pages)}"
            self.draw_text_wrapper(page_info, SCREEN_W - 60, SCREEN_H - 18, COLOR_DEBUG)

            if self.input.gamepad_available:
                self.draw_text_wrapper("GP", SCREEN_W - 90, SCREEN_H - 18, COLOR_DEBUG)

        end_drawing()

    def cleanup(self):
        self.sound.cleanup()
        if self.using_custom_font and hasattr(self, 'font') and self.font is not None:
            try:
                unload_font(self.font)
                self.using_custom_font = False
            except Exception:
                pass

    def run(self):
        try:
            while not window_should_close() and not self.should_quit:
                self.update()
                self.draw()
        finally:
            self.cleanup()
            close_window()


if __name__ == "__main__":
    app = App()
    app.run()
