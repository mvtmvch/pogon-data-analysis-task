# Zadanie rekrutacyjne - analiza danych

## Zadanie 1 - różnica xG według stanu meczu

### Wynik

Stan meczu definiuję z perspektywy Pogoni Grodzisk Mazowiecki. Stan Polonii jest w tych samych przedziałach lustrzany.

| Stan Pogoni   | xG Pogoni | Strzały Pogoni | xG Polonii | Strzały Polonii | Różnica xG Pogoni |
|---------------|----------:|---------------:|-----------:|----------------:|------------------:|
| prowadzenie   |      0.12 |              2 |       0.08 |               2 |         **+0.04** |
| remis         |      0.61 |             10 |       0.92 |              17 |         **-0.31** |
| przegrywanie  |      0.02 |              2 |       0.07 |               1 |         **-0.05** |

Różnica xG = xG Pogoni - xG Polonii. Dla Polonii są to te same wartości z przeciwnym znakiem w stanie lustrzanym: **+0.05** przy prowadzeniu, **+0.31** przy remisie, **-0.04** przy przegrywaniu.

Cały mecz: **Polonia 1.07 xG (20 strzałów), Pogoń 0.74 xG (14 strzałów), wynik 2-2**.

Większość meczu rozegrano przy remisie - na ten stan przypadło 27 z 34 strzałów. Pozostałe dwa stany obejmują łącznie tylko 7 strzałów, dlatego ich wartości należy interpretować ostrożnie.

Pełny wynik dla obu drużyn, wraz z liczbą strzałów i minutami, znajduje się w `results/xg_by_game_state.csv`.

### Definicja stanu meczu

Stan przypisuję na podstawie wyniku **bezpośrednio przed strzałem**.

Oznacza to, że strzał zmieniający wynik z 0-0 na 0-1 jest liczony jako oddany przy remisie. Gol wpływa dopiero na stan kolejnych zdarzeń.

Takie podejście pozwala analizować sytuacje strzeleckie w kontekście wyniku obowiązującego w momencie ich powstania.

### Przebieg wyniku

```text
 0:00 - 21:13    0-0    Pogoń remisuje
21:13 - 27:43    0-1    Pogoń prowadzi
27:43 - 36:18    1-1    Pogoń remisuje
36:18 - 45:37    2-1    Pogoń przegrywa
45:37 - 94:19    2-2    Pogoń remisuje
```

Wynik zapisany jako Polonia-Pogoń.

Wiersz `remis` w tabeli głównej jest sumą trzech rozłącznych fragmentów meczu: **0-0, 1-1 i 2-2**.

### Metodologia

Eksport StatsBomb ma format long - część zagnieżdżonych danych, m.in. `freeze_frame`, jest rozwinięta na dodatkowe wiersze.

| Dane                              | Liczba |
|-----------------------------------|-------:|
| wiersze w pliku                   |  3 892 |
| unikalne zdarzenia (`id`)         |  3 232 |
| wiersze `Shot`                    |    628 |
| **unikalne strzały**              | **34** |
| naiwna suma xG bez redukcji       |  32.71 |
| **poprawna suma xG**              | **1.81** |

Bez redukcji do poziomu pojedynczego zdarzenia suma xG wyniosłaby 32.71 zamiast poprawnego 1.81.

Analiza przebiega w następujący sposób:

1. Redukcja danych do jednego wiersza na zdarzenie na podstawie `id`.
2. Uporządkowanie zdarzeń chronologicznie według kolumny `index`.
3. Wybór zdarzeń `Shot` i wartości `statsbomb_xg`.
4. Odtworzenie wyniku meczu i przypisanie każdemu strzałowi stanu sprzed jego wykonania.
5. Agregacja xG oraz liczby strzałów według drużyny i stanu meczu.

### Walidacja

Po redukcji danych sprawdzam m.in., czy:

- każdy `id` reprezentuje dokładnie jedno zdarzenie,
- każdy strzał ma przypisaną wartość `statsbomb_xg` i dokładnie jeden stan meczu,
- suma xG oraz liczba strzałów po agregacji zgadzają się z wartościami dla całego meczu,
- odtworzony wynik końcowy wynosi 2-2, zgodnie z faktycznym rezultatem spotkania,
- wyniki obu drużyn zachowują oczekiwaną symetrię dla stanów lustrzanych.

Dodatkowo diagnostyka danych pokazuje, że 3 892 wiersze eksportu odpowiadają 3 232 unikalnym zdarzeniom, a 628 wierszy `Shot` - 34 unikalnym strzałom.

### Ograniczenia

- Analiza obejmuje tylko jeden mecz, dlatego nie służy do wyciągania szerszych wniosków o drużynach.
- Większość strzałów została oddana przy remisie, a próby dla prowadzenia i przegrywania są bardzo małe.
- Stan `remis` łączy sytuacje 0-0, 1-1 i 2-2, zgodnie z podziałem wygrana/remis/przegrana z treści zadania.

### Uruchomienie

```bash
python -m pip install -r requirements.txt
python src/xg_by_game_state.py
```

Skrypt oczekuje pliku:

```text
data/match_4068759.csv
```

Surowy plik dostarczony przez klub nie jest wersjonowany.

Wynik zapisywany jest do:

```text
results/xg_by_game_state.csv
```
