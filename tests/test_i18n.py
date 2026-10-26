import unittest

from ficbook_dl.formats.txt import render
from ficbook_dl.i18n import saved_status, t
from ficbook_dl.parse import Story


class LanguageTests(unittest.TestCase):
    def test_interface_strings(self):
        self.assertEqual(t("ru", "download"), "Скачать")
        self.assertEqual(t("uk", "download"), "Завантажити")
        self.assertEqual(t("en", "browse"), "Browse")

    def test_slavic_plurals(self):
        self.assertEqual(saved_status("ru", 1, 0), "Сохранена 1 работа.")
        self.assertEqual(saved_status("ru", 2, 0), "Сохранено 2 работы.")
        self.assertEqual(saved_status("ru", 5, 0), "Сохранено 5 работ.")
        self.assertEqual(saved_status("uk", 1, 0), "Збережено 1 роботу.")
        self.assertEqual(saved_status("uk", 5, 1), "Збережено 5 робіт. 1 помилка.")

    def test_text_header_follows_language(self):
        story = Story(story_id="1", title="Назва", author="Ім'я", url="https://ficbook.net/readfic/1", series_name="Цикл", series_index=2)
        self.assertIn("Автор: Ім'я", render(story, "uk"))
        self.assertIn("Серія: Цикл (2)", render(story, "uk"))
        self.assertIn("Автор: Ім'я", render(story, "ru"))
        self.assertIn("Серия: Цикл (2)", render(story, "ru"))


if __name__ == "__main__":
    unittest.main()
