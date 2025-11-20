import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import *  # импортируй все функции из твоего файла
from database import _get_connection

class TestDatabase:
    """Тесты для базы данных бота"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Создаем и очищаем базу перед каждым тестом"""
        global DB_NAME
        DB_NAME = 'test_ecostep.db'  # Используем тестовую БД
        
        # Инициализируем БД
        init_db()

        db_file = get_db_path()
        yield  # здесь выполняются тесты
        
        # Очистка после теста
        if os.path.exists(db_file):
            os.remove(db_file)
    
    def test_db_connection(self):
        """Тест подключения к БД"""
        conn = _get_connection()
        assert conn is not None
        
        # Проверяем что можем выполнять запросы
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
        conn.close()
    
    def test_tables_created(self):
        """Тест создания таблиц"""
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Проверяем существование таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {'users', 'user_challenges', 'custom_challenges', 'admin_logs'}
        assert expected_tables.issubset(tables)
        conn.close()
    
    def test_register_user(self):
        """Тест регистрации пользователя"""
        # Первая регистрация
        result1 = register_user(123, "test_user", "Test User")
        assert result1 is True
        
        # Повторная регистрация того же пользователя
        result2 = register_user(123, "test_user", "Test User")
        assert result2 is False
        
        # Проверяем что пользователь действительно создан
        user_info = get_user_info(123)
        assert user_info is not None
        assert user_info[0] == 123  # user_id
        assert user_info[1] == "test_user"  # username
    
    def test_get_user_info(self):
        """Тест получения информации о пользователе"""
        # Сначала регистрируем пользователя
        register_user(456, "john_doe", "John")
        
        # Получаем информацию
        user_info = get_user_info(456)
        assert user_info is not None
        assert user_info[0] == 456
        assert user_info[1] == "john_doe"
        assert user_info[2] == "John"
        
        # Проверяем несуществующего пользователя
        non_existent = get_user_info(999)
        assert non_existent is None
    
    def test_accept_challenge(self):
        """Тест принятия челленджа"""
        register_user(111, "user1", "User One")
        
        # Принимаем челлендж
        result = accept_challenge(111, "challenge_1")
        assert result is True
        
        # Проверяем статусы
        statuses = get_user_challenge_statuses(111)
        assert "challenge_1" in statuses
        assert statuses["challenge_1"] == "accepted"
        
        # Пытаемся принять уже отправленный челлендж
        mark_challenge_submitted(111, "challenge_1", "file_123", "Test caption")
        result_again = accept_challenge(111, "challenge_1")
        assert result_again is False
    
    def test_decline_challenge(self):
        """Тест отказа от челленджа"""
        register_user(222, "user2", "User Two")
        accept_challenge(222, "challenge_2")
        
        # Отказываемся от челленджа
        result = decline_challenge(222, "challenge_2")
        assert result is True
        
        # Проверяем что челлендж удален
        statuses = get_user_challenge_statuses(222)
        assert "challenge_2" not in statuses
        
        # Пытаемся отказаться от несуществующего челленджа
        result_fake = decline_challenge(222, "fake_challenge")
        assert result_fake is False
    
    def test_mark_challenge_submitted(self):
        """Тест отправки отчета по челленджу"""
        register_user(333, "user3", "User Three")
        accept_challenge(333, "challenge_3")
        
        # Отправляем отчет
        result = mark_challenge_submitted(
            user_id=333,
            challenge_id="challenge_3",
            file_id="photo_123",
            caption="My submission",
            attachment_type="photo",
            attachment_name="image.jpg"
        )
        assert result is True
        
        # Проверяем статус
        statuses = get_user_challenge_statuses(333)
        assert statuses["challenge_3"] == "submitted"
        
        # Проверяем данные отчета
        submitted = get_submitted_challenges(333)
        assert len(submitted) == 1
        assert submitted[0][0] == "challenge_3"  # challenge_id
        assert submitted[0][3] == "photo_123"  # file_id
        assert submitted[0][4] == "My submission"  # caption
    
    def test_custom_challenges(self):
        """Тест работы с кастомными челленджами"""
        # Сначала очистим существующие челленджи
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM custom_challenges")
        conn.commit()
        conn.close()
        
        # Создаем кастомный челлендж
        challenge_id = create_custom_challenge(
            title="Test Challenge",
            description="Test Description", 
            points=100,
            co2="10kg",
            co2_quantity_based=True,
        )
        assert challenge_id.startswith("custom_")
        
        # Получаем список кастомных челленджей
        challenges = fetch_custom_challenges()
        assert len(challenges) == 1
        assert challenges[0]["title"] == "Test Challenge"
        assert challenges[0]["points"] == 100
        assert challenges[0]["co2_quantity_based"] is True
        print("Кастомные челленджи работают")
    
    def test_admin_logs(self):
        """Тест логов администратора"""
        # Сначала очистим логи
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_logs")
        conn.commit()
        conn.close()
        
        # Добавляем запись в логи
        log_admin_action(123, "login", "User logged in")
        log_admin_action(123, "create_challenge", "Created new challenge")
        
        # Получаем логи
        logs = get_admin_logs(limit=10)
        assert len(logs) == 2
        assert logs[1]["action"] == "create_challenge"
        assert logs[0]["action"] == "login"
        assert logs[0]["admin_id"] == 123
        print("Логи администратора работают")
    
    def test_pending_reports(self):
        """Тест получения отчетов на модерацию"""
        # Очистим существующие данные
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_challenges")
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
        
        register_user(444, "user4", "User Four")
        register_user(555, "user5", "User Five")
        
        # Создаем и отправляем отчеты
        accept_challenge(444, "challenge_4")
        mark_challenge_submitted(444, "challenge_4", "file_444", "Caption 444")
        
        accept_challenge(555, "challenge_5") 
        mark_challenge_submitted(555, "challenge_5", "file_555", "Caption 555")
        
        # Получаем отчеты на модерацию
        pending = get_pending_reports()
        assert len(pending) == 2
        
        # Проверяем данные
        assert pending[0]["user_id"] == 444
        assert pending[0]["challenge_id"] == "challenge_4"
        assert pending[1]["user_id"] == 555
        print("Отчеты на модерацию работают")

    def test_report_review(self):
        """Тест модерации отчетов"""
        register_user(666, "user6", "User Six")
        accept_challenge(666, "challenge_6")
        mark_challenge_submitted(666, "challenge_6", "file_666", "Caption 6")
        
        # Одобряем отчет
        result_approve = update_report_review(
            user_id=666,
            challenge_id="challenge_6",
            review_status="approved",
            review_comment="Good job!",
            awarded_points=100,
            co2_saved=1.5,
        )
        assert result_approve is True
        
        # Проверяем статус
        review_statuses = get_user_review_statuses(666)
        assert review_statuses["challenge_6"] == "approved"
        
        # Проверяем начисленные баллы
        points = get_user_awarded_points(666)
        assert len(points) == 1
        assert points[0][1] == 100  # points_awarded
        assert points[0][3] == 1.5
    
    def test_user_review_summary(self):
        """Тест сводки по модерации"""
        register_user(777, "user7", "User Seven")
        
        # Создаем несколько отчетов с разными статусами
        accept_challenge(777, "challenge_pending")
        mark_challenge_submitted(777, "challenge_pending", "file_1", "Pending")
        
        accept_challenge(777, "challenge_approved")
        mark_challenge_submitted(777, "challenge_approved", "file_2", "Approved")
        update_report_review(777, "challenge_approved", "approved", awarded_points=50, co2_saved=0.5)
        
        accept_challenge(777, "challenge_rejected")
        mark_challenge_submitted(777, "challenge_rejected", "file_3", "Rejected")
        update_report_review(777, "challenge_rejected", "rejected")
        
        # Проверяем сводку
        summary = get_user_review_summary(777)
        assert summary.get("pending", 0) == 1
        assert summary.get("approved", 0) == 1
        assert summary.get("rejected", 0) == 1


# Дополнительные утилиты для тестирования
def run_all_tests():
    """Запуск всех тестов"""
    import subprocess
    result = subprocess.run(['pytest', __file__, '-v'], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    return result.returncode == 0


def quick_test():
    """Быстрый тест основных функций"""
    print("Запуск быстрого теста базы данных...")
    
    # Временно меняем БД для теста
    global DB_NAME
    original_db = DB_NAME
    DB_NAME = 'quick_test.db'
    
    try:
        init_db()
        
        # Тест пользователей
        register_user(999, "test", "Test User")
        user = get_user_info(999)
        assert user is not None
        print("Регистрация пользователя - OK")
        
        # Тест челленджей
        accept_challenge(999, "test_challenge")
        statuses = get_user_challenge_statuses(999)
        assert "test_challenge" in statuses
        print("Принятие челленджа - OK")
        
        # Тест отправки отчета
        mark_challenge_submitted(999, "test_challenge", "test_file", "Test caption")
        submitted = get_submitted_challenges(999)
        assert len(submitted) > 0
        print("Отправка отчета - OK")
        
        # Тест кастомных челленджей
        challenge_id = create_custom_challenge("Test", "Desc", 50, "5kg")
        challenges = fetch_custom_challenges()
        assert len(challenges) > 0
        print("Кастомные челленджи - OK")
        
        print("Все основные тесты пройдены!")
        
    finally:
        # Восстанавливаем оригинальную БД и чистим тестовую
        test_db_path = get_db_path()
        DB_NAME = original_db
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    # Запуск быстрого теста при прямом выполнении
    quick_test()
