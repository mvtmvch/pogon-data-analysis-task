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

Sam mecz był ubogi w sytuacje: 34 strzały dały łącznie 1.81 xG, czyli 0.053 na strzał (mediana 0.043), a próg 0.20 przekroczył tylko jeden z nich. Cztery gole padły z pozycji wartych razem 0.335 xG, więc wynik 2-2 leży wyraźnie powyżej tego, co obie drużyny wypracowały. Pogoń oddała pierwszy strzał dopiero w 21. minucie i od razu był to gol - do tego momentu Polonia miała 4 strzały i 0.229 xG.

Pełny wynik dla obu drużyn, wraz z liczbą strzałów i minutami, znajduje się w `results/xg_by_game_state.csv`.

### Definicja stanu meczu

Stan przypisuję na podstawie wyniku **bezpośrednio przed strzałem**.

Oznacza to, że strzał zmieniający wynik z 0-0 na 0-1 jest liczony jako oddany przy remisie. Gol wpływa dopiero na stan kolejnych zdarzeń.

Wybór konwencji waży na wyniku: przy odwrotnej (stan po strzale) te same dane dają +0.27 / -0.44 / -0.15 zamiast +0.04 / -0.31 / -0.05.

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

Skrypt przerywa działanie, jeśli którakolwiek z kontroli nie przejdzie. Sprawdzam, czy:

- każda czytana kolumna ma stałą wartość w obrębie `id` - dopiero to uprawnia do redukcji duplikatów,
- `index` zdarzeń tworzy pełny ciąg 1..N, czyli eksport nie jest ucięty ani przefiltrowany,
- każdy strzał ma `statsbomb_xg`, drużynę i policzalny czas od pierwszego gwizdka,
- liczba goli ze strzałów zgadza się z liczbą zdarzeń `Goal Conceded`, a mecz nie ma samobójów ani dogrywki,
- odtworzony wynik końcowy to 2-2, zgodnie z protokołem meczu.

Celowo nie sprawdzam tożsamości wynikających wprost z konstrukcji kodu - na przykład że różnica xG równa się xG For minus xG Against. Taka kontrola nie może nie przejść i tylko rozmywa te, które coś wnoszą.

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

## Zadanie 2 - czy zawodnik X nadaje się na wahadłowego

### Czego właściwie szukamy?

W nowoczesnym futbolu wahadłowy może pełnić bardzo różne funkcje. W jednym systemie zapewnia szerokość i gra niemal jak skrzydłowy, w innym schodzi do półprzestrzeni i uczestniczy w rozegraniu. Różnić mogą się nawet zadania obu wahadłowych w tej samej drużynie, co było widać chociażby przy różnych profilach Frimponga i Grimaldo w Bayerze Leverkusen Xabiego Alonso.

Dlatego przed rozpoczęciem analizy chciałbym ustalić, czego trener oczekuje od zawodnika w naszym systemie. Czy to on ma zapewniać szerokość? Jak wysoko powinien grać? Czy ma tworzyć sytuacje dryblingiem, dośrodkowaniem czy kombinacją? Kto asekuruje przestrzeń za nim? Czy po stracie ma odbudowywać formację, czy natychmiast pressować? Dopiero wtedy można przełożyć wymagania roli na konkretne zachowania i metryki.

### Czy 20 meczów to rzeczywiście 20 meczów?

Najpierw sprawdziłbym rzeczywiste minuty, pozycję, stronę boiska, wyjściową formację i jej zmiany w trakcie spotkania. Nie łączyłbym automatycznie występów jako RWB, RB i RW, bo w każdej z tych ról zawodnik ma inne zadania i inne okazje do wykonywania określonych działań. Uwzględniłbym także game state - inaczej wygląda profil zawodnika, gdy jego drużyna prowadzi i broni niżej, a inaczej, gdy przegrywa i przez ostatnie 20 minut atakuje.

Kluczowa jest również liczba zdarzeń. Jeżeli po segmentacji zostałoby 1400 minut jako RWB i przykładowo 70 dośrodkowań, próba wyglądałaby rozsądnie tylko do momentu, w którym podzielę ją na strefę, typ dośrodkowania, presję i fazę gry. Wtedy w niektórych grupach może pozostać po kilka lub kilkanaście obserwacji. Przy takim wolumenie pojedynczy mecz może wyraźnie zmienić wynik, dlatego obok wartości per 90 pokazałbym surową liczbę zdarzeń i rozkład mecz po meczu.

Szczególnie ostrożnie traktowałbym rzadkie działania. W eksporcie dostarczonym do zadania 1 `pass_cut_back` pojawia się dwa razy w całym meczu, na obie drużyny - przy takiej częstotliwości cutback prowadzący do strzału da przez 20 meczów kilka obserwacji i nie da się z nich czytać różnic.

### Co czytam z danych?

Zacząłbym od profilu przestrzennego: miejsc przyjęć, podań, prowadzeń i działań defensywnych. Dostępne pole `location_bucket` pozwala od razu rozdzielić akcje według sektorów boiska, a `pass_cluster_label` daje typologię podań według tercji, kanału, kierunku, długości i wysokości zagrania - w meczu z zadania 1 jest ich 39, na przykład `Midfield third - Center - To right - Short - Ground Pass`. Sama heatmapa nie będzie jednak pełnym obrazem pozycjonowania, ponieważ pokazuje miejsca zarejestrowanych działań, a nie pozycję zawodnika przez całą akcję.

Przy podaniach nie ograniczałbym się do ogólnej celności. W dostarczonym eksporcie znajduje się `pass_success_probability`, więc zamiast pytać, kto ma wyższą celność, czyzawodnik, który stale wycofuje piłkę do stopera, czy ten, który próbuje trudniejszych podań progresywnych, po prostu sprawdziłbym różnicę między rzeczywistą a oczekiwaną skutecznością. Pozwoliłoby to częściowo oddzielić jakość wykonania od trudności podejmowanych prób.

Analizowałbym również progresję z konkretnych stref, podania do ostatniej tercji i pola karnego oraz sposób kreacji. Zapisałbym przy tym dokładną definicję progressive pass, ponieważ nie jest to jedna uniwersalna kategoria i między źródłami potrafi oznaczać co innego. Pola `pass_cross`, `pass_cut_back` i `pass_switch` pozwalają rozdzielić typy zagrań bez ręcznej klasyfikacji. Z kolei `obv_for_net`, `obv_against_net` i `obv_total_net` pozwalają spojrzeć nie tylko na liczbę działań, ale również na ich wpływ na sytuację zespołu. Nie pytałbym więc wyłącznie, ile zawodnik wykonał dośrodkowań, lecz czy wybierał odpowiednie rozwiązanie i jaką wartość ono przynosiło.

Drybling również interpretowałbym w kontekście roli. Jego mała liczba nie musi być wadą, jeżeli system pozwala zdobywać przestrzeń przez kombinacje. Jeśli jednak wahadłowy ma sam odpowiadać za szerokość i regularnie mierzyć się z obrońcą w izolacji, skuteczność w ofensywnych pojedynkach 1v1 staje się jedną z kluczowych cech profilu. Podobnie przy stratach pytałbym nie tylko, ile ich było, ale gdzie wystąpiły i z jakiego ryzyka wynikały.

W defensywie wykorzystałbym lokalizację działań, `under_pressure`, `counterpress` oraz pola `defensive_responsibility_*`. Sama liczba odbiorów niewiele mówi. Wysoka liczba działań defensywnych nie musi oznaczać dobrej obrony, bo może wynikać z dobrej antycypacji, ale również z tego, że rywale regularnie atakują stronę zawodnika. Zależy też od tego, jak długo zespół pozostaje bez piłki i to jest właśnie problem, który metryki possession-adjusted rozwiązywały z grubsza, a Defensive Responsibility zastępuje, przestając karać zawodnika za to, że jego drużyna rzadko ma piłkę.

W eksporcie mam warstwę atrybucji tego modelu, czyli `defensive_responsibility_pressure_like`, `defensive_responsibility_interception_like` oraz prawdopodobieństwa odpowiedzialności per zawodnik. Z nich i z `obv_against_net` policzyłbym, ile wartości przeciwnika przechodziło przez jego strefę odpowiedzialności i jak wypadał względem oczekiwanej liczby interwencji. Nadal sprawdziłbym tackles, interceptions i dribbled past, ale nie traktowałbym ich jako samodzielnej oceny jakości bronienia.

Nie pominąłbym również gry w powietrzu. Wahadłowy schodzący do linii pięciu może odpowiadać za zamknięcie dalszego słupka, dlatego sprawdziłbym jego pojedynki powietrzne, `duel_win_probability` oraz pola `hops_*`. HOPS uwzględnia poziom przeciwnika w pojedynku i próbuje lepiej ocenić umiejętność gry głową niż zwykły procent wygranych starć. Trzeba jednak pamiętać, że jest to rating budowany na historii zawodnika i ważony w stronę niedawnych pojedynków, a nie statystyka z tych 20 meczów. Nie podlega więc problemowi małej próby w takim stopniu jak reszta, ale też nie opisuje dokładnie okresu, który analizuję, dlatego obok ratingu podałbym liczbę pojedynków zawodnika w samej próbie.

Wyniki porównałbym przede wszystkim z zawodnikami wykonującymi podobne zadania w naszym zespole lub taktycznie zbliżonych drużynach. Percentyl względem wszystkich bocznych obrońców w lidze potraktowałbym jedynie pomocniczo, ponieważ taka grupa miesza różne role i style gry.

### Gdzie te dane zawiodą?

Standardowe event data opisują pojedyncze zdarzenia, a nie ciągły ruch zawodników. Nie pokażą więc wiarygodnie, czy zawodnik utrzymuje szerokość, kiedy nie dostaje piłki, jak dobiera timing overlapu, jak szybko wraca po stracie ani czy prawidłowo śledzi przeciwnika na dalszym słupku. Nie zobaczymy również części dobrych zachowań w defensywnym 1v1, takich jak spowolnienie przeciwnika, wypchnięcie go na słabszą nogę czy zamknięcie linii podania bez próby odbioru. Dane nie pozwolą też ocenić maksymalnej prędkości, HSR ani zdolności do powtarzania intensywnych biegów. StatsBomb 360 poprawiłby kontekst przestrzenny, ale nadal nie zastąpi trackingu, GPS-u i wideo.

Dlatego dane wykorzystałbym do ukierunkowania obserwacji. Na wideo sprawdziłbym przede wszystkim defensywne 1v1, reakcje po stracie, zamykanie dalszego słupka, momenty wyjścia do pressingu oraz ruchy bez piłki, po których zawodnik nie otrzymał podania. Nie ograniczałbym się tylko do jego najlepszych akcji.

### Co oddaję?

Końcowym produktem byłaby jedna strona z pięcioma do siedmiu wymaganiami wynikającymi z naszego systemu. Przy każdym znalazłaby się ocena, krótki dowód liczbowy, wielkość próby i poziom pewności. Osobno wskazałbym rzeczy, których nie da się ocenić na podstawie danych. Na dole znalazłaby się prosta rekomendacja: tak, nie albo obserwować dalej, wraz z najważniejszym argumentem i największym ryzykiem.
