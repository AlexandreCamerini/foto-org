# 11 — Dados estáticos: tabelas, constantes e textos literais que a reconstrução precisa copiar

> Gerado automaticamente em 2026-09-20 a partir do código de `524903d` (importando os módulos e lendo o catálogo real com `SELECT`). Regenerar: `scripts`-livre — o gerador está no histórico desta sessão; se divergir do código, o código manda. Cada seção cita `arquivo:linha` da definição.

## TEMPLATE_PADRAO (`fotoorganizer/classification/templates.py:24`)

```
{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}
```

## DESTINO_NAO_FOTO (`fotoorganizer/classification/templates.py:29`)

```
Não são fotos
```

## ROTULOS — `tipo_imagem` → rótulo de pasta (`fotoorganizer/classification/tipo_imagem.py:39`)

| tipo_imagem | rótulo |
|---|---|
| `foto` | `foto` |
| `captura` | `captura de tela` |
| `recebida` | `recebida em mensageiro` |
| `baixada` | `baixada da web` |

## _TELAS — resoluções de tela reconhecidas como captura (`fotoorganizer/classification/tipo_imagem.py:84`)

Total: 46 pares (já inclui transpostos).

```
[(768, 1366), (828, 1792), (900, 1440), (1080, 1920), (1080, 2340), (1080, 2400), (1125, 2436), (1170, 2532), (1179, 2556), (1242, 2688), (1284, 2778), (1290, 2796), (1366, 768), (1440, 900), (1440, 2560), (1536, 2048), (1600, 2560), (1668, 2224), (1668, 2388), (1792, 828), (1800, 2880), (1920, 1080), (1920, 3072), (1964, 3024), (2048, 1536), (2048, 2732), (2160, 3840), (2224, 1668), (2234, 3456), (2340, 1080), (2388, 1668), (2400, 1080), (2436, 1125), (2532, 1170), (2556, 1179), (2560, 1440), (2560, 1600), (2688, 1242), (2732, 2048), (2778, 1284), (2796, 1290), (2880, 1800), (3024, 1964), (3072, 1920), (3456, 2234), (3840, 2160)]
```

## _ROTULOS_CAMPO — campos da escrita EXIF (`fotoorganizer/exif_write/executor.py:82`)

| chave | valor |
|---|---|
| `gps` | `GPS` |
| `cidade` | `Cidade` |
| `pais` | `País` |

## Constantes numéricas (nome → valor)

| constante | valor — definição |
|---|---|
| `GAP_NOVA_VIAGEM` | `datetime.timedelta(days=3) — fotoorganizer/grouping/temporal.py:13` |
| `LIMIAR_VISUAL` | `8 — fotoorganizer/duplicates/detector.py:50` |
| `_LOTE_SUMICO` | `500 — fotoorganizer/scanner/scanner.py:68` |
| `COBERTURA_MEDIDA` | `0.936 — fotoorganizer/grouping/correlacao.py:84` |
| `VELOCIDADE_PLAUSIVEL_MS` | `6.0 — fotoorganizer/grouping/correlacao.py:69` |
| `RAIO_PISO_M` | `15.0 — fotoorganizer/grouping/correlacao.py:72` |
| `RAIO_TETO_M` | `50000.0 — fotoorganizer/grouping/correlacao.py:78` |
| `FATOR` | `6.0 — fotoorganizer/grouping/eventos_temporais.py:60` |
| `JANELA` | `12 — fotoorganizer/grouping/eventos_temporais.py:79` |
| `PISO` | `datetime.timedelta(seconds=5400) — fotoorganizer/grouping/eventos_temporais.py:56` |
| `TETO` | `datetime.timedelta(seconds=28800) — fotoorganizer/grouping/eventos_temporais.py:58` |
| `DESLOCAMENTO_KM` | `3.0 — fotoorganizer/grouping/eventos_temporais.py:63` |
| `MIN_FOTOS_EVENTO` | `10 — fotoorganizer/grouping/eventos_temporais.py:88` |
| `DURACAO_MAX_ACONTECIMENTO` | `datetime.timedelta(seconds=72000) — fotoorganizer/grouping/eventos_temporais.py:73` |
| `_BATCH_SIZE` | `200 — fotoorganizer/sources/importer.py:36` |
| `_EXTRACAO_TIMEOUT_S` | `120.0 — fotoorganizer/scanner/scanner.py:64` |
| `_CHUNK` | `262144 — fotoorganizer/security/hashing.py:17` |

## NOTA_DO_RAIO (`fotoorganizer/grouping/correlacao.py:482`)

```
O círculo é o tamanho da dúvida, não um erro de medição: em 93,6% dos pares medidos neste acervo, o lugar verdadeiro cabe dentro dele.
```

## LACUNAS (`fotoorganizer/repositories/media.py:98`)

| chave | valor |
|---|---|
| `sem_data` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `sem_gps` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `local_estimado` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `nao_e_foto` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `tipo_a_confirmar` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `sem_grupo` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `sem_camera` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `sem_sugestao` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `confianca_baixa` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `confianca_media` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `erro_leitura` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |

## ALCANCES (`fotoorganizer/repositories/media.py:90`)

| chave | valor |
|---|---|
| `tudo` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `organizaveis` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |
| `faltantes` | `str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to sys.getdefaultencoding().
errors defaults to 'strict'.` |

## PAISES_PT — nomes de país em português → código (`fotoorganizer/geolocation/paises.py:21`)

Total: 250.

| nome | código |
|---|---|
| `AD` | `Andorra` |
| `AE` | `Emirados Árabes Unidos` |
| `AF` | `Afeganistão` |
| `AG` | `Antígua e Barbuda` |
| `AI` | `Anguilla` |
| `AL` | `Albânia` |
| `AM` | `Armênia` |
| `AO` | `Angola` |
| `AQ` | `Antártida` |
| `AR` | `Argentina` |
| `AS` | `Samoa Americana` |
| `AT` | `Áustria` |
| `AU` | `Austrália` |
| `AW` | `Aruba` |
| `AX` | `Ilhas Åland` |
| `AZ` | `Azerbaijão` |
| `BA` | `Bósnia e Herzegovina` |
| `BB` | `Barbados` |
| `BD` | `Bangladesh` |
| `BE` | `Bélgica` |
| `BF` | `Burkina Faso` |
| `BG` | `Bulgária` |
| `BH` | `Bahrein` |
| `BI` | `Burundi` |
| `BJ` | `Benin` |
| `BL` | `São Bartolomeu` |
| `BM` | `Bermudas` |
| `BN` | `Brunei` |
| `BO` | `Bolívia` |
| `BQ` | `Países Baixos Caribenhos` |
| `BR` | `Brasil` |
| `BS` | `Bahamas` |
| `BT` | `Butão` |
| `BV` | `Ilha Bouvet` |
| `BW` | `Botsuana` |
| `BY` | `Belarus` |
| `BZ` | `Belize` |
| `CA` | `Canadá` |
| `CC` | `Ilhas Cocos` |
| `CD` | `República Democrática do Congo` |
| `CF` | `República Centro-Africana` |
| `CG` | `República do Congo` |
| `CH` | `Suíça` |
| `CI` | `Costa do Marfim` |
| `CK` | `Ilhas Cook` |
| `CL` | `Chile` |
| `CM` | `Camarões` |
| `CN` | `China` |
| `CO` | `Colômbia` |
| `CR` | `Costa Rica` |
| `CU` | `Cuba` |
| `CV` | `Cabo Verde` |
| `CW` | `Curaçao` |
| `CX` | `Ilha Christmas` |
| `CY` | `Chipre` |
| `CZ` | `Tchéquia` |
| `DE` | `Alemanha` |
| `DJ` | `Djibuti` |
| `DK` | `Dinamarca` |
| `DM` | `Dominica` |
| `DO` | `República Dominicana` |
| `DZ` | `Argélia` |
| `EC` | `Equador` |
| `EE` | `Estônia` |
| `EG` | `Egito` |
| `EH` | `Saara Ocidental` |
| `ER` | `Eritreia` |
| `ES` | `Espanha` |
| `ET` | `Etiópia` |
| `FI` | `Finlândia` |
| `FJ` | `Fiji` |
| `FK` | `Ilhas Malvinas` |
| `FM` | `Micronésia` |
| `FO` | `Ilhas Faroe` |
| `FR` | `França` |
| `GA` | `Gabão` |
| `GB` | `Reino Unido` |
| `GD` | `Granada` |
| `GE` | `Geórgia` |
| `GF` | `Guiana Francesa` |
| `GG` | `Guernsey` |
| `GH` | `Gana` |
| `GI` | `Gibraltar` |
| `GL` | `Groenlândia` |
| `GM` | `Gâmbia` |
| `GN` | `Guiné` |
| `GP` | `Guadalupe` |
| `GQ` | `Guiné Equatorial` |
| `GR` | `Grécia` |
| `GS` | `Geórgia do Sul e Sandwich do Sul` |
| `GT` | `Guatemala` |
| `GU` | `Guam` |
| `GW` | `Guiné-Bissau` |
| `GY` | `Guiana` |
| `HK` | `Hong Kong` |
| `HM` | `Ilha Heard e Ilhas McDonald` |
| `HN` | `Honduras` |
| `HR` | `Croácia` |
| `HT` | `Haiti` |
| `HU` | `Hungria` |
| `ID` | `Indonésia` |
| `IE` | `Irlanda` |
| `IL` | `Israel` |
| `IM` | `Ilha de Man` |
| `IN` | `Índia` |
| `IO` | `Território Britânico do Oceano Índico` |
| `IQ` | `Iraque` |
| `IR` | `Irã` |
| `IS` | `Islândia` |
| `IT` | `Itália` |
| `JE` | `Jersey` |
| `JM` | `Jamaica` |
| `JO` | `Jordânia` |
| `JP` | `Japão` |
| `KE` | `Quênia` |
| `KG` | `Quirguistão` |
| `KH` | `Camboja` |
| `KI` | `Kiribati` |
| `KM` | `Comores` |
| `KN` | `São Cristóvão e Névis` |
| `KP` | `Coreia do Norte` |
| `KR` | `Coreia do Sul` |
| `KW` | `Kuwait` |
| `KY` | `Ilhas Cayman` |
| `KZ` | `Cazaquistão` |
| `LA` | `Laos` |
| `LB` | `Líbano` |
| `LC` | `Santa Lúcia` |
| `LI` | `Liechtenstein` |
| `LK` | `Sri Lanka` |
| `LR` | `Libéria` |
| `LS` | `Lesoto` |
| `LT` | `Lituânia` |
| `LU` | `Luxemburgo` |
| `LV` | `Letônia` |
| `LY` | `Líbia` |
| `MA` | `Marrocos` |
| `MC` | `Mônaco` |
| `MD` | `Moldávia` |
| `ME` | `Montenegro` |
| `MF` | `São Martinho` |
| `MG` | `Madagascar` |
| `MH` | `Ilhas Marshall` |
| `MK` | `Macedônia do Norte` |
| `ML` | `Mali` |
| `MM` | `Mianmar` |
| `MN` | `Mongólia` |
| `MO` | `Macau` |
| `MP` | `Ilhas Marianas do Norte` |
| `MQ` | `Martinica` |
| `MR` | `Mauritânia` |
| `MS` | `Montserrat` |
| `MT` | `Malta` |
| `MU` | `Maurício` |
| `MV` | `Maldivas` |
| `MW` | `Malaui` |
| `MX` | `México` |
| `MY` | `Malásia` |
| `MZ` | `Moçambique` |
| `NA` | `Namíbia` |
| `NC` | `Nova Caledônia` |
| `NE` | `Níger` |
| `NF` | `Ilha Norfolk` |
| `NG` | `Nigéria` |
| `NI` | `Nicarágua` |
| `NL` | `Países Baixos` |
| `NO` | `Noruega` |
| `NP` | `Nepal` |
| `NR` | `Nauru` |
| `NU` | `Niue` |
| `NZ` | `Nova Zelândia` |
| `OM` | `Omã` |
| `PA` | `Panamá` |
| `PE` | `Peru` |
| `PF` | `Polinésia Francesa` |
| `PG` | `Papua-Nova Guiné` |
| `PH` | `Filipinas` |
| `PK` | `Paquistão` |
| `PL` | `Polônia` |
| `PM` | `São Pedro e Miquelão` |
| `PN` | `Ilhas Pitcairn` |
| `PR` | `Porto Rico` |
| `PS` | `Palestina` |
| `PT` | `Portugal` |
| `PW` | `Palau` |
| `PY` | `Paraguai` |
| `QA` | `Catar` |
| `RE` | `Reunião` |
| `RO` | `Romênia` |
| `RS` | `Sérvia` |
| `RU` | `Rússia` |
| `RW` | `Ruanda` |
| `SA` | `Arábia Saudita` |
| `SB` | `Ilhas Salomão` |
| `SC` | `Seicheles` |
| `SD` | `Sudão` |
| `SE` | `Suécia` |
| `SG` | `Singapura` |
| `SH` | `Santa Helena` |
| `SI` | `Eslovênia` |
| `SJ` | `Svalbard e Jan Mayen` |
| `SK` | `Eslováquia` |
| `SL` | `Serra Leoa` |
| `SM` | `San Marino` |
| `SN` | `Senegal` |
| `SO` | `Somália` |
| `SR` | `Suriname` |
| `SS` | `Sudão do Sul` |
| `ST` | `São Tomé e Príncipe` |
| `SV` | `El Salvador` |
| `SX` | `Sint Maarten` |
| `SY` | `Síria` |
| `SZ` | `Essuatíni` |
| `TC` | `Ilhas Turks e Caicos` |
| `TD` | `Chade` |
| `TF` | `Terras Austrais Francesas` |
| `TG` | `Togo` |
| `TH` | `Tailândia` |
| `TJ` | `Tajiquistão` |
| `TK` | `Toquelau` |
| `TL` | `Timor-Leste` |
| `TM` | `Turcomenistão` |
| `TN` | `Tunísia` |
| `TO` | `Tonga` |
| `TR` | `Turquia` |
| `TT` | `Trinidad e Tobago` |
| `TV` | `Tuvalu` |
| `TW` | `Taiwan` |
| `TZ` | `Tanzânia` |
| `UA` | `Ucrânia` |
| `UG` | `Uganda` |
| `UM` | `Ilhas Menores Distantes dos EUA` |
| `US` | `Estados Unidos` |
| `UY` | `Uruguai` |
| `UZ` | `Uzbequistão` |
| `VA` | `Vaticano` |
| `VC` | `São Vicente e Granadinas` |
| `VE` | `Venezuela` |
| `VG` | `Ilhas Virgens Britânicas` |
| `VI` | `Ilhas Virgens Americanas` |
| `VN` | `Vietnã` |
| `VU` | `Vanuatu` |
| `WF` | `Wallis e Futuna` |
| `WS` | `Samoa` |
| `XK` | `Kosovo` |
| `YE` | `Iêmen` |
| `YT` | `Mayotte` |
| `ZA` | `África do Sul` |
| `ZM` | `Zâmbia` |
| `ZW` | `Zimbábue` |

## TZ_POR_PAIS — código de país → fuso IANA (`fotoorganizer/geolocation/timezones.py:54`)

Total: 250.

| país | IANA |
|---|---|
| `Afeganistão` | `Asia/Kabul` |
| `Albânia` | `Europe/Tirane` |
| `Alemanha` | `Europe/Berlin` |
| `Andorra` | `Europe/Andorra` |
| `Angola` | `Africa/Luanda` |
| `Anguilla` | `America/Anguilla` |
| `Antártida` | `Antarctica/McMurdo` |
| `Antígua e Barbuda` | `America/Antigua` |
| `Argentina` | `America/Argentina/Buenos_Aires` |
| `Argélia` | `Africa/Algiers` |
| `Armênia` | `Asia/Yerevan` |
| `Aruba` | `America/Aruba` |
| `Arábia Saudita` | `Asia/Riyadh` |
| `Austrália` | `Australia/Sydney` |
| `Azerbaijão` | `Asia/Baku` |
| `Bahamas` | `America/Nassau` |
| `Bahrein` | `Asia/Bahrain` |
| `Bangladesh` | `Asia/Dhaka` |
| `Barbados` | `America/Barbados` |
| `Belarus` | `Europe/Minsk` |
| `Belize` | `America/Belize` |
| `Benin` | `Africa/Porto-Novo` |
| `Bermudas` | `Atlantic/Bermuda` |
| `Bolívia` | `America/La_Paz` |
| `Botsuana` | `Africa/Gaborone` |
| `Brasil` | `America/Sao_Paulo` |
| `Brunei` | `Asia/Brunei` |
| `Bulgária` | `Europe/Sofia` |
| `Burkina Faso` | `Africa/Ouagadougou` |
| `Burundi` | `Africa/Bujumbura` |
| `Butão` | `Asia/Thimphu` |
| `Bélgica` | `Europe/Brussels` |
| `Bósnia e Herzegovina` | `Europe/Sarajevo` |
| `Cabo Verde` | `Atlantic/Cape_Verde` |
| `Camarões` | `Africa/Douala` |
| `Camboja` | `Asia/Phnom_Penh` |
| `Canadá` | `America/Toronto` |
| `Catar` | `Asia/Qatar` |
| `Cazaquistão` | `Asia/Almaty` |
| `Chade` | `Africa/Ndjamena` |
| `Chile` | `America/Santiago` |
| `China` | `Asia/Shanghai` |
| `Chipre` | `Asia/Nicosia` |
| `Colômbia` | `America/Bogota` |
| `Comores` | `Indian/Comoro` |
| `Coreia do Norte` | `Asia/Pyongyang` |
| `Coreia do Sul` | `Asia/Seoul` |
| `Costa Rica` | `America/Costa_Rica` |
| `Costa do Marfim` | `Africa/Abidjan` |
| `Croácia` | `Europe/Zagreb` |
| `Cuba` | `America/Havana` |
| `Curaçao` | `America/Curacao` |
| `Dinamarca` | `Europe/Copenhagen` |
| `Djibuti` | `Africa/Djibouti` |
| `Dominica` | `America/Dominica` |
| `Egito` | `Africa/Cairo` |
| `El Salvador` | `America/El_Salvador` |
| `Emirados Árabes Unidos` | `Asia/Dubai` |
| `Equador` | `America/Guayaquil` |
| `Eritreia` | `Africa/Asmara` |
| `Eslováquia` | `Europe/Bratislava` |
| `Eslovênia` | `Europe/Ljubljana` |
| `Espanha` | `Europe/Madrid` |
| `Essuatíni` | `Africa/Mbabane` |
| `Estados Unidos` | `America/New_York` |
| `Estônia` | `Europe/Tallinn` |
| `Etiópia` | `Africa/Addis_Ababa` |
| `Fiji` | `Pacific/Fiji` |
| `Filipinas` | `Asia/Manila` |
| `Finlândia` | `Europe/Helsinki` |
| `França` | `Europe/Paris` |
| `Gabão` | `Africa/Libreville` |
| `Gana` | `Africa/Accra` |
| `Geórgia` | `Asia/Tbilisi` |
| `Geórgia do Sul e Sandwich do Sul` | `Atlantic/South_Georgia` |
| `Gibraltar` | `Europe/Gibraltar` |
| `Granada` | `America/Grenada` |
| `Groenlândia` | `America/Nuuk` |
| `Grécia` | `Europe/Athens` |
| `Guadalupe` | `America/Guadeloupe` |
| `Guam` | `Pacific/Guam` |
| `Guatemala` | `America/Guatemala` |
| `Guernsey` | `Europe/Guernsey` |
| `Guiana` | `America/Guyana` |
| `Guiana Francesa` | `America/Cayenne` |
| `Guiné` | `Africa/Conakry` |
| `Guiné Equatorial` | `Africa/Malabo` |
| `Guiné-Bissau` | `Africa/Bissau` |
| `Gâmbia` | `Africa/Banjul` |
| `Haiti` | `America/Port-au-Prince` |
| `Honduras` | `America/Tegucigalpa` |
| `Hong Kong` | `Asia/Hong_Kong` |
| `Hungria` | `Europe/Budapest` |
| `Ilha Bouvet` | `Etc/GMT` |
| `Ilha Christmas` | `Indian/Christmas` |
| `Ilha Heard e Ilhas McDonald` | `Indian/Kerguelen` |
| `Ilha Norfolk` | `Pacific/Norfolk` |
| `Ilha de Man` | `Europe/Isle_of_Man` |
| `Ilhas Cayman` | `America/Cayman` |
| `Ilhas Cocos` | `Indian/Cocos` |
| `Ilhas Cook` | `Pacific/Rarotonga` |
| `Ilhas Faroe` | `Atlantic/Faroe` |
| `Ilhas Malvinas` | `Atlantic/Stanley` |
| `Ilhas Marianas do Norte` | `Pacific/Saipan` |
| `Ilhas Marshall` | `Pacific/Majuro` |
| `Ilhas Menores Distantes dos EUA` | `Pacific/Wake` |
| `Ilhas Pitcairn` | `Pacific/Pitcairn` |
| `Ilhas Salomão` | `Pacific/Guadalcanal` |
| `Ilhas Turks e Caicos` | `America/Grand_Turk` |
| `Ilhas Virgens Americanas` | `America/St_Thomas` |
| `Ilhas Virgens Britânicas` | `America/Tortola` |
| `Ilhas Åland` | `Europe/Mariehamn` |
| `Indonésia` | `Asia/Jakarta` |
| `Iraque` | `Asia/Baghdad` |
| `Irlanda` | `Europe/Dublin` |
| `Irã` | `Asia/Tehran` |
| `Islândia` | `Atlantic/Reykjavik` |
| `Israel` | `Asia/Jerusalem` |
| `Itália` | `Europe/Rome` |
| `Iêmen` | `Asia/Aden` |
| `Jamaica` | `America/Jamaica` |
| `Japão` | `Asia/Tokyo` |
| `Jersey` | `Europe/Jersey` |
| `Jordânia` | `Asia/Amman` |
| `Kiribati` | `Pacific/Tarawa` |
| `Kosovo` | `Europe/Belgrade` |
| `Kuwait` | `Asia/Kuwait` |
| `Laos` | `Asia/Vientiane` |
| `Lesoto` | `Africa/Maseru` |
| `Letônia` | `Europe/Riga` |
| `Libéria` | `Africa/Monrovia` |
| `Liechtenstein` | `Europe/Vaduz` |
| `Lituânia` | `Europe/Vilnius` |
| `Luxemburgo` | `Europe/Luxembourg` |
| `Líbano` | `Asia/Beirut` |
| `Líbia` | `Africa/Tripoli` |
| `Macau` | `Asia/Macau` |
| `Macedônia do Norte` | `Europe/Skopje` |
| `Madagascar` | `Indian/Antananarivo` |
| `Malaui` | `Africa/Blantyre` |
| `Maldivas` | `Indian/Maldives` |
| `Mali` | `Africa/Bamako` |
| `Malta` | `Europe/Malta` |
| `Malásia` | `Asia/Kuala_Lumpur` |
| `Marrocos` | `Africa/Casablanca` |
| `Martinica` | `America/Martinique` |
| `Mauritânia` | `Africa/Nouakchott` |
| `Maurício` | `Indian/Mauritius` |
| `Mayotte` | `Indian/Mayotte` |
| `Mianmar` | `Asia/Yangon` |
| `Micronésia` | `Pacific/Pohnpei` |
| `Moldávia` | `Europe/Chisinau` |
| `Mongólia` | `Asia/Ulaanbaatar` |
| `Montenegro` | `Europe/Podgorica` |
| `Montserrat` | `America/Montserrat` |
| `Moçambique` | `Africa/Maputo` |
| `México` | `America/Mexico_City` |
| `Mônaco` | `Europe/Monaco` |
| `Namíbia` | `Africa/Windhoek` |
| `Nauru` | `Pacific/Nauru` |
| `Nepal` | `Asia/Kathmandu` |
| `Nicarágua` | `America/Managua` |
| `Nigéria` | `Africa/Lagos` |
| `Niue` | `Pacific/Niue` |
| `Noruega` | `Europe/Oslo` |
| `Nova Caledônia` | `Pacific/Noumea` |
| `Nova Zelândia` | `Pacific/Auckland` |
| `Níger` | `Africa/Niamey` |
| `Omã` | `Asia/Muscat` |
| `Palau` | `Pacific/Palau` |
| `Palestina` | `Asia/Gaza` |
| `Panamá` | `America/Panama` |
| `Papua-Nova Guiné` | `Pacific/Port_Moresby` |
| `Paquistão` | `Asia/Karachi` |
| `Paraguai` | `America/Asuncion` |
| `Países Baixos` | `Europe/Amsterdam` |
| `Países Baixos Caribenhos` | `America/Kralendijk` |
| `Peru` | `America/Lima` |
| `Polinésia Francesa` | `Pacific/Tahiti` |
| `Polônia` | `Europe/Warsaw` |
| `Porto Rico` | `America/Puerto_Rico` |
| `Portugal` | `Europe/Lisbon` |
| `Quirguistão` | `Asia/Bishkek` |
| `Quênia` | `Africa/Nairobi` |
| `Reino Unido` | `Europe/London` |
| `República Centro-Africana` | `Africa/Bangui` |
| `República Democrática do Congo` | `Africa/Kinshasa` |
| `República Dominicana` | `America/Santo_Domingo` |
| `República do Congo` | `Africa/Brazzaville` |
| `Reunião` | `Indian/Reunion` |
| `Romênia` | `Europe/Bucharest` |
| `Ruanda` | `Africa/Kigali` |
| `Rússia` | `Europe/Moscow` |
| `Saara Ocidental` | `Africa/El_Aaiun` |
| `Samoa` | `Pacific/Apia` |
| `Samoa Americana` | `Pacific/Pago_Pago` |
| `San Marino` | `Europe/San_Marino` |
| `Santa Helena` | `Atlantic/St_Helena` |
| `Santa Lúcia` | `America/St_Lucia` |
| `Seicheles` | `Indian/Mahe` |
| `Senegal` | `Africa/Dakar` |
| `Serra Leoa` | `Africa/Freetown` |
| `Singapura` | `Asia/Singapore` |
| `Sint Maarten` | `America/Lower_Princes` |
| `Somália` | `Africa/Mogadishu` |
| `Sri Lanka` | `Asia/Colombo` |
| `Sudão` | `Africa/Khartoum` |
| `Sudão do Sul` | `Africa/Juba` |
| `Suriname` | `America/Paramaribo` |
| `Suécia` | `Europe/Stockholm` |
| `Suíça` | `Europe/Zurich` |
| `Svalbard e Jan Mayen` | `Arctic/Longyearbyen` |
| `São Bartolomeu` | `America/St_Barthelemy` |
| `São Cristóvão e Névis` | `America/St_Kitts` |
| `São Martinho` | `America/Marigot` |
| `São Pedro e Miquelão` | `America/Miquelon` |
| `São Tomé e Príncipe` | `Africa/Sao_Tome` |
| `São Vicente e Granadinas` | `America/St_Vincent` |
| `Sérvia` | `Europe/Belgrade` |
| `Síria` | `Asia/Damascus` |
| `Tailândia` | `Asia/Bangkok` |
| `Taiwan` | `Asia/Taipei` |
| `Tajiquistão` | `Asia/Dushanbe` |
| `Tanzânia` | `Africa/Dar_es_Salaam` |
| `Tchéquia` | `Europe/Prague` |
| `Terras Austrais Francesas` | `Indian/Kerguelen` |
| `Território Britânico do Oceano Índico` | `Indian/Chagos` |
| `Timor-Leste` | `Asia/Dili` |
| `Togo` | `Africa/Lome` |
| `Tonga` | `Pacific/Tongatapu` |
| `Toquelau` | `Pacific/Fakaofo` |
| `Trinidad e Tobago` | `America/Port_of_Spain` |
| `Tunísia` | `Africa/Tunis` |
| `Turcomenistão` | `Asia/Ashgabat` |
| `Turquia` | `Europe/Istanbul` |
| `Tuvalu` | `Pacific/Funafuti` |
| `Ucrânia` | `Europe/Kyiv` |
| `Uganda` | `Africa/Kampala` |
| `Uruguai` | `America/Montevideo` |
| `Uzbequistão` | `Asia/Tashkent` |
| `Vanuatu` | `Pacific/Efate` |
| `Vaticano` | `Europe/Vatican` |
| `Venezuela` | `America/Caracas` |
| `Vietnã` | `Asia/Ho_Chi_Minh` |
| `Wallis e Futuna` | `Pacific/Wallis` |
| `Zimbábue` | `Africa/Harare` |
| `Zâmbia` | `Africa/Lusaka` |
| `África do Sul` | `Africa/Johannesburg` |
| `Áustria` | `Europe/Vienna` |
| `Índia` | `Asia/Kolkata` |

## Prompt de sistema — advisor de cluster (`fotoorganizer/classification/advisor.py:_SYSTEM`)

```
Você classifica grupos de fotos de um acervo pessoal a partir de METADADOS (nomes de pastas e arquivos, datas, lugares). Você nunca vê as imagens. Responda apenas o que os metadados sustentam: nomes de pasta como 'Serena 15 Anos' indicam aniversário (Eventos); estadias de dias em outro país indicam Viagens. Se os metadados não bastarem, devolva categoria e evento nulos — nunca invente.
```

## Prompt de sistema — classificação de pasta (GenAI de pasta) (`fotoorganizer/classification/location_advisor.py:_SYSTEM`)

```
Você classifica PASTAS de um acervo de fotos pessoal. Você recebe apenas
o nome da pasta e metadado já catalogado (contagem de fotos, período) —
nunca a imagem, nunca um caminho de arquivo, nunca uma miniatura.

Para cada pasta, proponha, quando der para concluir com segurança:

- "cidade" / "pais": onde as fotos foram tiradas, se o nome da pasta
  permitir concluir isso.
- "categoria": uma de "Viagens", "Família" ou "Eventos" — o mesmo
  vocabulário que o app já usa para agrupar pastas.
- "evento": um nome curto do acontecimento/viagem, se o nome da pasta
  sugerir um.

Regras:
- NUNCA invente. Se o nome da pasta não permitir concluir com segurança,
  devolva `null` no campo — essa é a resposta válida e preferida, não
  uma falha.
- Cada pasta traz `campos_a_preencher`: só proponha valor para os campos
  ali listados. Nunca proponha um campo que não foi pedido.
- Cada pasta traz `ja_conhecido`: campos que já têm valor confirmado.
  Nunca proponha um valor para um campo que já aparece em `ja_conhecido`
  daquela pasta — ele já tem dono e não deve ser reescrito.
- "justificativa" explica em uma frase curta, em português, de onde veio
  a conclusão (ex.: "nome da pasta é um topônimo conhecido").
- Responda TODAS as pastas recebidas, com a grafia exata em que vieram.

```

## Prompt de sistema — léxico de nomes (`fotoorganizer/classification/lexico.py:_SYSTEM`)

```
Você classifica NOMES DE PASTA e NOMES DE ÁLBUM de um acervo de fotos
pessoal. Você recebe apenas as palavras — nunca as imagens, datas ou
coordenadas.

Para cada nome, responda uma categoria:

- "lugar": um lugar aonde se viaja ou se vai. Cidade, região, país, parque,
  praia, serra, bairro, estabelecimento. Ex.: "Pantanal", "Chapada dos
  Veadeiros", "Visconde de Mauá", "Aiuruoca e Tiradentes", "Dubai".
- "ocasiao": um acontecimento com hora marcada. Festa, aniversário,
  casamento, formatura, show, espetáculo, cerimônia, competição. Ex.:
  "Serena 15 Anos", "Quizomba", "Casamento da Ana", "Teatro".
- "pessoa": o nome de uma pessoa ou de um grupo de pessoas, sem indicar
  acontecimento. Ex.: "Vovó", "Meninas", "Família Silva".
- "ruido": não é acervo de foto pessoal. Nome de câmera ou equipamento,
  pasta de programação ou build, cache de aplicativo, identificador
  técnico, hash, pasta de sistema. Ex.: "Canon EOS 5D Mark IV",
  "DerivedData-access004", "node_modules", "CapCut", "Bora.build",
  "581ef37ff7c241daa5b2e8b1643a6e70".

Regras:
- Um nome pode ser as duas coisas ("Réveillon em Paraty" é ocasião E lugar).
  Escolha o que o nome enfatiza; na dúvida entre lugar e ocasião, prefira
  "lugar" apenas quando o nome for reconhecidamente um topônimo.
- Nome que você não reconhece e que não parece técnico: classifique pelo que
  a forma sugere e diga isso na justificativa. Não invente familiaridade.
- Responda TODOS os nomes recebidos, na mesma grafia em que vieram.

```

## MENSAGEM_GATE_FECHADO (409 literal) (`fotoorganizer/server/genai_pasta.py:MENSAGEM_GATE_FECHADO`)

```
Classificação de pasta por IA está desligada — habilite os dois consentimentos (serviços externos e o opt-in do recurso) antes de continuar.
```

## MENSAGEM_MESTRE_DESLIGADO (409 literal) (`fotoorganizer/server/genai_pasta.py:MENSAGEM_MESTRE_DESLIGADO`)

```
Serviços externos estão desligados nas configurações do app — habilite [privacidade] servicos_externos antes de usar este recurso.
```

## Contratos JSON citados sem shape no mapa (trecho literal do código)

### `_sugestao_json` (linha da Revisão)

`fotoorganizer/server/app.py:245`

```python
def _sugestao_json(linha: SuggestionRow, fora: frozenset[int] = frozenset()) -> dict:
    return {
        "id": linha.id,
        "media_id": linha.media_id,
        "nome": linha.nome,
        "pasta": linha.pasta,
        "destino": linha.destino,
        "nivel": linha.nivel.value,
        "status": linha.status.value,
        "data_capturada": (
            linha.data_capturada.isoformat() if linha.data_capturada else None
        ),
        "camera": linha.camera,
        "gps_estimado": linha.gps_estimado,
        "source_id": linha.source_id,
        # Por que a foto não pode ser aberta agora (a tela diz em vez de
        # desenhar imagem quebrada). None quando está alcançável.
        "motivo_indisponivel": (
            "sem arquivo neste Mac" if linha.arquivo_ausente
            else "volume ou pasta fora de alcance"
            if linha.source_id in fora else None
        ),
    }
```

### `linha_do_tempo` (repositório)

`fotoorganizer/repositories/media.py:470`

```python
    def linha_do_tempo(self, filters: MediaFilters) -> list[dict]:
        """Quantas fotos por mês, no recorte atual e na ordem da grade.

        É o que torna 100 mil fotos alcançáveis: sem isto, rolar é a única
        forma de chegar em 2015. Uma consulta agregada, não uma varredura —
        o banco conta por mês em milissegundos e a grade não precisa ter
        carregado a página onde aquele mês começa.
        """
        mes = func.strftime("%Y-%m", MediaFile.data_capturada)
        base = self._query(filters).subquery()
        alias = aliased(MediaFile, base)
        mes_alias = func.strftime("%Y-%m", alias.data_capturada)
        with self._factory() as session:
            linhas = session.execute(
                select(mes_alias, func.count(alias.id))
                .group_by(mes_alias)
                .order_by(mes_alias.desc())
            ).all()
        return [
            {"mes": m, "quantidade": n}
            for m, n in linhas if m is not None
        ]
```

### `cruzamento_ano_fonte` (dentro do inventário/panorama)

`fotoorganizer/repositories/media.py:578`

```python
                "cruzamento_ano_fonte": [
                    {
                        "ano": ano or "sem data",
                        "source_id": source_id,
                        "quantidade": n,
                    }
                    for ano, source_id, n in session.execute(
                        select(
                            ano_expr, MediaFile.source_id,
                            func.count(MediaFile.id),
                        ).where(proprias).group_by(ano_expr, MediaFile.source_id)
                    )
                ],
            }
```

### `GET /api/status`

`fotoorganizer/server/app.py:498`

```python
    @app.get("/api/status")
    def status() -> dict:
        stats = media_repo.estatisticas()
        return {"versao": __version__, **stats}

    @app.get("/api/funil")
```

## `evidence.campo` e `evidence.origem` — valores que existem de fato no catálogo real (2026-09-20)

| campo | linhas |
|---|---|
| `data` | `55096` |
| `ano` | `32484` |
| `categoria` | `24637` |
| `pais` | `22233` |
| `viagem` | `16567` |
| `regiao` | `9469` |
| `evento` | `7673` |
| `cidade` | `6988` |
| `tipo` | `422` |

| origem | linhas |
|---|---|
| `exif` | `53967` |
| `pasta` | `53928` |
| `geocoding_offline` | `36772` |
| `vizinhanca_temporal` | `20240` |
| `vizinhanca` | `7506` |
| `album_externo` | `1605` |
| `fs` | `1121` |
| `arquivo` | `422` |
| `nome_arquivo` | `8` |

| nivel | linhas |
|---|---|
| `ALTA` | `90776` |
| `BAIXA` | `5077` |
| `MEDIA` | `79716` |

## Cenários do benchmark `scripts/avaliar_agrupamento.py` (passo 2 do gate)

Total: 19 cenários rotulados; o gate exige N/N.

1. aniversário 15 anos, 5h
2. álbum nomeado (Quizomba), 4h
3. pasta técnica de data, 2h
4. pasta cronológica 'mês dia' sem ano, 2h
5. pasta cronológica 'dia de mês de ano' por extenso, 2h
6. pasta Viagens/, 1 dia
7. país na pasta, 2h
8. GPS 450km de casa, 1 dia
9. estadia 5 dias, GPS, casa DESCONHECIDA
10. fim de semana 300km de casa
11. festa de 4h com GPS em casa
12. férias EM CASA: 6 dias de GPS a 2km
13. casamento de fim de semana (keyword)
14. Natal (keyword), 2 dias
15. formatura, 3h
16. álbum longo (obra da casa, 10 dias)
17. home dir + data: nada nomeável
18. sessão de horas, GPS país sem casa
19. viagem multi-país, 21 dias, 9000km de casa

## Formato de `INVENTARIO.md` (gerado do `inventario.json`)

`fotoorganizer/operations/inventario.py:4`

```python
par `inventario.json` + `INVENTARIO.md` por PASTA de destino, aditivo
entre execuções de planos diferentes ao longo do tempo — nunca um par
por foto nem por plano.

Chamado só DEPOIS que `operations/executor.py` já verificou a cópia por
hash (`item.hash_pos == item.hash_pre`). Nunca decide se a cópia é
válida — só registra o que já foi verificado.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.models import (
    Location,
    MediaFile,
    OperationItem,
    Suggestion,
    SuggestionStatus,
)

log = logging.getLogger(__name__)

_GERADO_POR = "Foto Organizer"
```

## Timeout do writer EXIF

`fotoorganizer/exif_write/writer.py:126` — `subprocess.run(args, capture_output=True, text=True, check=False)` **sem `timeout`**; `verificacao.dump`/`dump_lote` usam 30 s. Uma reconstrução deve declarar timeout na escrita (ver `09-MELHORIAS.md`).

