# =============================================================================
# NFC COMPATIBILITY MATRIX - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/did_config/nfc_compatibility.py
# Дата: 2026-01-28
# Опис: Матриця сумісності форм випуску NFC1
# =============================================================================

"""
Матриця клінічної сумісності NFC1 для проекту cross_pharm_market_analysis.

БІЗНЕС-ПРАВИЛО:
    - Тільки 3 пероральні форми можуть замінювати одна одну
    - Всі інші форми - тільки Exact Match (на себе)

Логіка:
    - ORAL_GROUP: пероральні форми взаємозамінні
    - EXACT_MATCH: інші форми замінюються тільки на себе
    - EXCLUDED: не для медичного використання

Використання:
    from project_core.did_config.nfc_compatibility import (
        is_compatible,
        get_compatibility_group,
        ORAL_GROUP
    )
"""

from typing import List


# =============================================================================
# NFC1 GROUPS
# =============================================================================

# Єдина група взаємозамінних форм (пероральні)
ORAL_GROUP: List[str] = [
    "Пероральные твердые обычные",                # Таблетки, капсули
    "Пероральные жидкие обычные",                 # Сиропи, розчини
    "Пероральные твердые длительно действующие"   # Ретард-форми
]

# Категорії що виключаються з аналізу (не медичні)
EXCLUDE_FORMS: List[str] = [
    "Не предназначенные для использования у человека и прочие"
]

# Всі відомі категорії NFC1 (для валідації)
ALL_NFC1_CATEGORIES: List[str] = [
    "Пероральные твердые обычные",
    "Местно действующие, дерматологические, антигеморроидальные, наружные",
    "Парентеральные обычные",
    "Пероральные жидкие обычные",
    "Ректальные системные",
    "Пероральные твердые длительно действующие",
    "Офтальмологические",
    "Прочие системные",
    "Не предназначенные для использования у человека и прочие"
]


# =============================================================================
# COMPATIBILITY FUNCTIONS
# =============================================================================

def is_compatible(form_a: str, form_b: str) -> bool:
    """
    Перевірка клінічної сумісності форм випуску NFC1.

    ПРАВИЛА:
    0. Виключені форми (EXCLUDE_FORMS) → завжди False
    1. Exact Match (form_a == form_b) → True
    2. Обидві форми в ORAL_GROUP → True
    3. Всі інші комбінації → False

    Args:
        form_a: NFC1_ID першого препарату
        form_b: NFC1_ID другого препарату

    Returns:
        bool: True якщо форми можуть замінювати одна одну

    Examples:
        >>> is_compatible("Пероральные твердые обычные", "Пероральные жидкие обычные")
        True  # Обидві в ORAL_GROUP

        >>> is_compatible("Пероральные твердые обычные", "Парентеральные обычные")
        False  # Різні групи

        >>> is_compatible("Парентеральные обычные", "Парентеральные обычные")
        True  # Exact Match
    """
    # ПРАВИЛО 0: Виключені форми - завжди НІ
    if form_a in EXCLUDE_FORMS or form_b in EXCLUDE_FORMS:
        return False

    # ПРАВИЛО 1: Exact Match - завжди ТАК
    if form_a == form_b:
        return True

    # ПРАВИЛО 2: ORAL_GROUP - тільки ці 3 форми можуть замінювати одна одну
    if form_a in ORAL_GROUP and form_b in ORAL_GROUP:
        return True

    # ПРАВИЛО 3: Всі інші комбінації - НІ
    return False


def get_compatibility_group(form: str) -> str:
    """
    Визначити групу сумісності для форми випуску.

    Args:
        form: NFC1_ID форми випуску

    Returns:
        str: 'ORAL', 'EXACT_MATCH', або 'EXCLUDED'
    """
    if form in EXCLUDE_FORMS:
        return 'EXCLUDED'
    elif form in ORAL_GROUP:
        return 'ORAL'
    else:
        return 'EXACT_MATCH'


def get_compatible_forms(form: str) -> List[str]:
    """
    Отримати список сумісних форм для заданої форми.

    Args:
        form: NFC1_ID форми випуску

    Returns:
        List[str]: Список сумісних форм (включаючи саму форму)
    """
    if form in EXCLUDE_FORMS:
        return []

    if form in ORAL_GROUP:
        return ORAL_GROUP.copy()

    # Для інших форм - тільки Exact Match
    return [form]


def filter_compatible_substitutes(
    target_nfc1: str,
    substitutes_nfc1: List[str]
) -> List[str]:
    """
    Відфільтрувати сумісні substitutes по NFC1.

    Args:
        target_nfc1: NFC1 target препарату
        substitutes_nfc1: Список NFC1 потенційних substitutes

    Returns:
        List[str]: Список сумісних NFC1
    """
    return [nfc1 for nfc1 in substitutes_nfc1 if is_compatible(target_nfc1, nfc1)]


# =============================================================================
# STATISTICS
# =============================================================================

def get_nfc1_statistics() -> dict:
    """
    Отримати статистику по групах NFC1.

    Returns:
        dict: Статистика категорій
    """
    oral_count = len(ORAL_GROUP)
    exclude_count = len(EXCLUDE_FORMS)
    exact_match_count = len(ALL_NFC1_CATEGORIES) - oral_count - exclude_count

    return {
        'total_categories': len(ALL_NFC1_CATEGORIES),
        'oral_group': oral_count,
        'excluded': exclude_count,
        'exact_match': exact_match_count
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate_matrix() -> bool:
    """
    Валідація матриці сумісності.

    Перевіряє що всі категорії покриті.

    Returns:
        bool: True якщо валідація пройшла
    """
    # Перевірка що ORAL_GROUP є підмножиною ALL_NFC1_CATEGORIES
    for form in ORAL_GROUP:
        if form not in ALL_NFC1_CATEGORIES:
            print(f"ПОМИЛКА: {form} не в ALL_NFC1_CATEGORIES")
            return False

    # Перевірка що EXCLUDE_FORMS є підмножиною ALL_NFC1_CATEGORIES
    for form in EXCLUDE_FORMS:
        if form not in ALL_NFC1_CATEGORIES:
            print(f"ПОМИЛКА: {form} не в ALL_NFC1_CATEGORIES")
            return False

    # Перевірка симетричності is_compatible
    for form_a in ALL_NFC1_CATEGORIES:
        for form_b in ALL_NFC1_CATEGORIES:
            if is_compatible(form_a, form_b) != is_compatible(form_b, form_a):
                print(f"ПОМИЛКА: Асиметрія для {form_a} і {form_b}")
                return False

    return True


# Автоматична валідація при імпорті
if __name__ != "__main__":
    validate_matrix()


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("NFC COMPATIBILITY MATRIX - cross_pharm_market_analysis")
    print("=" * 80)

    stats = get_nfc1_statistics()
    print(f"\nСтатистика NFC1:")
    print(f"  Всього категорій: {stats['total_categories']}")
    print(f"  ORAL_GROUP (взаємозамінні): {stats['oral_group']}")
    print(f"  EXCLUDED (виключені): {stats['excluded']}")
    print(f"  EXACT_MATCH (тільки на себе): {stats['exact_match']}")

    print("\n" + "=" * 80)
    print("ORAL_GROUP (можуть замінювати одна одну):")
    print("=" * 80)
    for form in ORAL_GROUP:
        print(f"  + {form}")

    print("\n" + "=" * 80)
    print("EXACT MATCH (тільки на себе):")
    print("=" * 80)
    for form in ALL_NFC1_CATEGORIES:
        if form not in ORAL_GROUP and form not in EXCLUDE_FORMS:
            print(f"  = {form}")

    print("\n" + "=" * 80)
    print("EXCLUDED (виключені з аналізу):")
    print("=" * 80)
    for form in EXCLUDE_FORMS:
        print(f"  x {form}")

    print("\n" + "=" * 80)
    print("ПРИКЛАДИ:")
    print("=" * 80)

    examples = [
        ("Пероральные твердые обычные", "Пероральные жидкие обычные"),
        ("Пероральные твердые обычные", "Парентеральные обычные"),
        ("Парентеральные обычные", "Парентеральные обычные"),
        ("Офтальмологические", "Ректальные системные"),
    ]

    for form_a, form_b in examples:
        result = is_compatible(form_a, form_b)
        emoji = "+" if result else "x"
        print(f"  {emoji} {form_a[:35]}... + {form_b[:35]}... = {result}")

    print(f"\nValidation: {'PASSED' if validate_matrix() else 'FAILED'}")
