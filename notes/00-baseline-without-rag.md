# Experiment 00 — Baseline: asking the model without any documents

**Date:** 2026-09-17
**Model:** `nvidia/nemotron-3-super-120b-a12b` (NVIDIA NIM)
**Setup:** `hello_nim.py`, no retrieval, no tools, `temperature=1.0`, same prompt run 3 times.
**System prompt:** "You are a helpful assistant. Answer in Turkish, briefly."
**Question:** "ODTÜ KKK'da ders ekleme-bırakma dönemi ne zaman ve kaç ders bırakabilirim??"

## Raw answers

**Run 1** (737 tokens)
> ODTÜ KKK'da ders ekleme-bırakma dönemi genellikle her dönemnin ilk 2 haftasıdır. Bu süre içinde istediğiniz kadar ders bırakabilirsiniz (ceza/sınır yok). Exact tarihler her yıl değişebileceği için, güncel akademik takvimi ODTÜ KKK resmi web sitesinden (örneğin, ODTÜ KKK Dekanlık veya Öğrenci İşleri sayfası) kontrol etmelisiniz. Dönem sonrası bırakma (Withdrawal) farklı kurallar uygulanır.

**Run 2** (1828 tokens)
> ODTÜ'de ders ekleme-bırakma dönemi genellikle dönemin ilk 2 haftasıdır. Bu dönemde sınırsız sayıda ders bırakabilirsiniz (akademik ceza yoktur). Ancak kesin tarihler ve uygulama detayları için所属学部または Kayıt Ofisi'ne danışmanız önerilir. (Not: "KKK" ifadesi standart ODTÜ birimini ifade etmiyor olabilir; belirsizlik durumunda üniversite kayıt ofisiyle doğrudan irtibata geçiniz.)

**Run 3** (873 tokens)
> ODTÜ'de ders ekleme-bırakma dönemi her sezonun ilk iki haftasıdır (örnek: Güz için Ekim başı, Bahar için Şubat başı). Bu dönemde ders sayısında sınır bırakmazsınız, ancak **en az 12 kredi** (tam zamanlı durum için minimum) alarak kalmalısınız. Kesin tarihler her yıl değişebileceğinden, ODTÜ Akademik Takvimi'ni kontrol edin ve danışmanınızla görüşün.

## Observations

1. **Inconsistent facts across runs.** A minimum-credit rule ("12 kredi") and concrete dates appear in only 1 of 3 runs. A claim that appears in one sample out of three is a strong hallucination signal.
2. **The model does not know the campus.** Run 2 says "KKK" may not be a real METU unit (it is the Northern Cyprus Campus), yet all runs state rules with confidence.
3. **High temperature leaks unlikely tokens.** Run 2 switches to Japanese mid-sentence (`所属学部または`); Run 1 mixes in English ("Exact").
4. **Cost is non-deterministic too.** Same prompt: 737 / 1828 / 873 tokens (reasoning model, variable thinking length).
5. **Disclaimers don't fix it.** Every answer ends with "check the official website", but the confident first sentence is what a student will act on.

**Correctness:** not yet verified — to be checked against the actual METU regulations in Phase 3.

## What this motivates

- Low temperature for answers (consistency) — but consistency is not correctness.
- Ground answers in the real regulation text (RAG) and cite the article.
- Refuse ("I couldn't find this in the regulations") instead of guessing.
- Measure answers repeatedly (Phase 4 eval), because one run proves nothing.
