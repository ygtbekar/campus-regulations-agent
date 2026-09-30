# End-to-end agent evaluation

28 questions (24 answerable, 4 out of scope). Judge model: `openai/gpt-oss-20b`.

| metric | result |
|---|---|
| Answer correct (correct) | 22/24 |
| Answer correct or partial | 23/24 |
| Cited the expected article | 24/24 |
| Refused out-of-scope question | 3/4 |
| Cited nothing when out of scope | 3/4 |

## Per question

| id | type | verdict | sources | question |
|---|---|---|---|---|
| q01 | in_scope | correct | MADDE 30 | İki dönem üst üste genel not ortalamam 2,00'ın altında kaldı. Sınamalı |
| q02 | partial | partial | MADDE 7 | Yaz okulunda hangi tür dersleri alabilirim? |
| q03 | in_scope | correct | MADDE 18 | Bir dönemde en fazla kaç ders alabilirim? |
| q04 | in_scope | correct | MADDE 18 | Genel ortalamam 2,60. Normal ders yüküne kaç ders ekleyebilirim? |
| q05 | in_scope | correct | MADDE 18 | Bir yarıyılda en az kaç ders almam gerekiyor? |
| q06 | in_scope | correct | MADDE 30 | Sınamalı öğrenciyim ve genel ortalamam 1,70. Daha önce hiç almadığım b |
| q07 | in_scope | correct | MADDE 22 | Bir dersten çekilmek istiyorum, bunu ne zaman yapabilirim? |
| q08 | in_scope | correct | MADDE 22 | Öğrenimim boyunca toplam kaç dersten çekilebilirim? |
| q09 | in_scope | correct | MADDE 22 | Birinci sınıftayım. Bu dönem aldığım bir dersten çekilebilir miyim? |
| q10 | in_scope | correct | MADDE 24, MADDE 27 | NA notu ne demek ve not ortalamama nasıl etki eder? |
| q11 | in_scope | correct | MADDE 24 | AA notunun katsayısı kaçtır, hangi puan aralığına karşılık gelir? |
| q12 | in_scope | correct | MADDE 31 | Mezun olabilmek için genel not ortalamam en az kaç olmalı? |
| q13 | in_scope | correct | MADDE 23 | Derslere devam etmek zorunlu mu? |
| q14 | in_scope | correct | MADDE 26 | Hangi notları aldığım dersleri tekrar almak zorundayım? |
| q15 | in_scope | correct | MADDE 26 | Geçtiğim bir dersi not yükseltmek için tekrar alabilir miyim? |
| q16 | in_scope | correct | MADDE 28 | Şeref veya yüksek şeref öğrencisi olmak için ortalamam kaç olmalı? |
| q17 | in_scope | correct | MADDE 40 | Bir yarıyıl izin almak (kayıt dondurmak) istiyorum, en fazla ne kadar  |
| q18 | in_scope | correct | MADDE 35 | Akademik danışmanımın görevleri neler? |
| q19 | in_scope | correct | MADDE 41 | Üniversiteden kaydımı sildirirsem tekrar aynı programa kayıt olabilir  |
| q20 | in_scope | correct | MADDE 7 | Bir eğitim öğretim yılı kaç hafta sürüyor? |
| q21 | partial | correct | MADDE 21 | Ders ekleme-bırakma işlemini ne zaman yapabilirim? |
| q22 | partial | correct | MADDE 32 | Bütünleme sınavı hakkım var mı, kuralları neler? |
| q23 | partial | wrong | MADDE 10 | Çift anadal programına başvuru koşulları neler? |
| q24 | partial | correct | MADDE 37 | Burs başvurusu için gereken belgeler neler? |
| q25 | out_of_scope | correct | — | Kampüs yemekhanesi hafta içi saat kaçta açılıyor? |
| q26 | out_of_scope | wrong | MADDE 21, MADDE 39 | Yurt başvuruları ne zaman başlıyor ve oda ücretleri ne kadar? |
| q27 | out_of_scope | correct | — | Öğrenci kulübüne nasıl üye olabilirim? |
| q28 | out_of_scope | correct | — | CENG 300 dersinin bu dönemki final sınavı hangi gün yapılacak? |
