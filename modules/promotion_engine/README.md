# promotion_engine

Block 8 реализует локальный planning-контур для будущей задачи `palmistry-pilot`.

Модуль принимает `PromotionBrief`, оценивает каналы и возвращает две первичные стратегии, фазы работ и approval gate. URL продукта валидируется как входное поле, но не запрашивается по сети.

Границы Block 8:

- no real API, credentials, publication, mailing or paid promotion;
- `execute()` намеренно остаётся stub и возвращает ошибку;
- manifest находится в `manifest.json` со статусом `inactive`;
- модуль создаёт только draft/awaiting-approval plan;
- `palmistry-pilot` как отдельная Task ещё не создаётся.

Публичный API находится в `engine.py`. Контракт — `contracts/promotion-plan.md`.
