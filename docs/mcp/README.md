# MCP Services Overview

| Service | Purpose | Responsibilities / Tools |
| --- | --- | --- |
| learner-memory | Store and retrieve learner progress | `get_profile`, `update_profile`, `record_mistake`, `get_progress` |
| curriculum | Control educational progression | `get_lesson`, `get_topic`, `get_scenario` |
| dictionary | Linguistic references | `lookup_word`, `get_examples`, `get_conjugation` |
| grammar | Explain and evaluate grammar | `lookup_rule`, `explain_rule`, `generate_exercise`, `grade_exercise` |
| locale | Handle dialects and regional differences | `get_locale`, `vocabulary_overrides`, `pronunciation_profile` |
| conversation | Generate roleplay experiences | `generate_scenario`, `evaluate_response`, `suggest_followup` |
| review | Spaced repetition | `get_due_words`, `schedule_review`, `record_review` |
| analytics | Learning analytics | Purpose: track learner outcomes, Responsibilities: summarise progress and engagement, Tools: `get_learning_summary`, `get_retention_report`, `get_engagement_overview` *(placeholders)* |
