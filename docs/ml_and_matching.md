# ML, извлечение навыков и matching

## Таксономия ролей

Начальные классы: `data_analyst`, `product_analyst`, `bi_analyst`, `business_analyst`, `system_analyst`, `marketing_analyst`, `financial_analyst`, `data_scientist`, `other_analytics`, `non_target`, `unclear`. Перед разметкой проверить, достаточно ли примеров; редкие классы допустимо объединить.

## Разметка

- Единица: каноническая вакансия, не snapshot.
- Поля для решения: title + description + key skills; работодатель не должен напрямую определять класс.
- Двойная разметка минимум 10% выборки, разногласия разрешаются арбитражем.
- Стратифицировать по поисковому запросу, времени, title и работодателю.
- Хранить `label`, `annotator`, `label_version`, `reason`, `labeled_at`.

## Модели

Baseline 1: правила title/negative patterns. Baseline 2: TF-IDF word (1-2) + char (3-5) n-grams, Logistic Regression с class weights при необходимости. Hybrid: high-precision rules, затем ML; confidence ниже порога -> `unclear`.

Split делать по времени и/или duplicate cluster. Нельзя распределять варианты одной публикации между train/test. Метрики: macro/weighted F1, per-class precision/recall/F1, confusion matrix, coverage; отдельно качество на ambiguous cases. Accuracy не использовать как единственный критерий.

Начальный gate: hybrid не хуже rule baseline по macro-F1 и повышает recall целевых ролей без неприемлемой потери precision. Численные пороги утвердить после baseline, не выдумывать заранее.

## Seniority и junior score

Buckets: `internship`, `genuine_junior`, `junior_hidden_experience`, `middle_plus`, `unclear`.

Компоненты score: explicit HH experience, годы в тексте, `стажер/junior/без опыта`, самостоятельное владение процессом, руководство, архитектурные обязанности, требования к стеку и образование. Не считать число технологий прямым эквивалентом seniority. Сохранять все сработавшие сигналы.

## Навыки

Словарь: canonical name, aliases, category, regex/boundaries, ambiguous flag. Категории: SQL/DB, Python/R, BI, spreadsheets, statistics/experiments, product analytics, data engineering, domain/soft skills.

Приоритет источников: структурированные `key_skills` -> требования description -> прочие секции. Тестировать `R`, `C`, `BI`, `1C`, `SQL` против ложных подстрок. Версионировать словарь. Синонимы (`powerbi`, `Power BI`) сводить к одному skill.

Метрики extractor: precision/recall/F1 на размеченных span/document labels, unknown terms report. Частотность навыка считать по уникальным representative vacancies.

## Повторные публикации

Кандидаты формируются блокировкой по normalized employer + близкому title + временному окну. Similarity считать по очищенному title/description; точные content hashes объединять сразу. Порог подбирать на ручной паре positive/negative. Кластеризация не должна объединять разные города/грейды без сильного подтверждения.

## Matching

Профиль YAML: target roles, target seniority, required/preferred skills, current skills, excluded employers/terms, locations/remote, salary floor, weights.

Начальная формула (веса конфигурируемы):

`score = 0.40 skill_coverage + 0.20 role_fit + 0.15 seniority_fit + 0.10 location_fit + 0.10 salary_fit + 0.05 freshness - penalties`.

Missing salary даёт neutral, а не 0. Required skill miss может быть penalty, но не обязательно hard filter. Вывод: total score, компоненты, matched skills, missing skills, фильтры/штрафы, причины рекомендации. Tie-break: score -> published_at -> vacancy_id.

Offline-проверка: 20-50 профилей/вакансий с ручной relevance; Precision@K, Recall@K/NDCG при достаточной разметке и качественный error analysis.
