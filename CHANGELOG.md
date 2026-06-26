# Changelog

## [1.7.0](https://github.com/andrewtryder/ha-voipms/compare/v1.6.0...v1.7.0) (2026-06-26)


### Features

* **integration:** add SIP registration monitoring via binary sensors ([a410929](https://github.com/andrewtryder/ha-voipms/commit/a4109295cbdb82492b06a91c553bb9aba7b7a775))
* **integration:** add SIP registration monitoring via binary sensors ([8d5738a](https://github.com/andrewtryder/ha-voipms/commit/8d5738a454b60b0b3cf326f2f4d6f5789a827146))

## [1.6.0](https://github.com/andrewtryder/ha-voipms/compare/v1.5.0...v1.6.0) (2026-06-25)


### Features

* **integration:** add call tracking, voicemail counter, and fix SMS sensor reversion ([bc00045](https://github.com/andrewtryder/ha-voipms/commit/bc0004574708e1db11b380a69cb84605c91a2265))
* **integration:** add call tracking, voicemail counter, and fix SMS sensor reversion ([068040d](https://github.com/andrewtryder/ha-voipms/commit/068040dfcf3e2b4a71167bdba38070bb237af75b))

## [1.5.0](https://github.com/andrewtryder/ha-voipms/compare/v1.4.0...v1.5.0) (2026-06-25)


### Features

* **format:** apply ruff formatting to all files ([0cd415c](https://github.com/andrewtryder/ha-voipms/commit/0cd415cfc197f51fcaac215af89cf1e8de8edfb0))
* **format:** apply ruff formatting to all files ([8e5d928](https://github.com/andrewtryder/ha-voipms/commit/8e5d9287743c8425ac2fe2655c772c1ad2aa6475))


### Bug Fixes

* **__init__:** re-expose VoipMsRestClient and add get_url function ([e9a8a3f](https://github.com/andrewtryder/ha-voipms/commit/e9a8a3ff8ed0f489a4ce1d3848e97cc394a7fa71))
* **__init__:** remove unused imports and explicitly re-export client and coordinator (ruff F401) ([e53eb20](https://github.com/andrewtryder/ha-voipms/commit/e53eb201d321c34ed87c99aeaf6ab8ffaf728825))
* **integration:** restore setup entry and resolve CI failures ([02b9973](https://github.com/andrewtryder/ha-voipms/commit/02b997305dd2d7281696babc7f04aa51c2cc656e))
* resolve ruff linting issues ([de3fd7e](https://github.com/andrewtryder/ha-voipms/commit/de3fd7e1734483ce54e82f227ffc0e5b471462df))
* **test_processor:** fix unused variable 'notifications' (ruff F841) ([390a7ba](https://github.com/andrewtryder/ha-voipms/commit/390a7baf784c76b688ffcbc5590959815f1258bf))
* **tests:** remove unused variable assignment 'notifications' (ruff F841) ([cdd950e](https://github.com/andrewtryder/ha-voipms/commit/cdd950ee24f421b923298ada7be126a6b07bdbf7))

## [1.4.0](https://github.com/andrewtryder/ha-voipms/compare/v1.3.3...v1.4.0) (2026-06-24)


### Features

* **notify:** add SMS card and dedicated send_sms service ([d1ecf95](https://github.com/andrewtryder/ha-voipms/commit/d1ecf95eebf758b008a10407868bbd09887c1f57))
* **notify:** add SMS card and dedicated send_sms service ([6d69c7f](https://github.com/andrewtryder/ha-voipms/commit/6d69c7f626bb7ed713f808bde21e76f9d6ae9633))


### Bug Fixes

* **notify:** add services.yaml for hassfest validation ([f3760a1](https://github.com/andrewtryder/ha-voipms/commit/f3760a1c397319f9908b35aafb8525cef5e3e8d3))

## [1.3.3](https://github.com/andrewtryder/ha-voipms/compare/v1.3.2...v1.3.3) (2026-06-24)


### Bug Fixes

* **sms:** add Activity logbook entries and fix CDR/balance polling ([bdf0c72](https://github.com/andrewtryder/ha-voipms/commit/bdf0c72052c2f062e03fc13f0d1d542282e994bb))
* **sms:** add Activity logbook entries and fix CDR/balance polling ([9905cac](https://github.com/andrewtryder/ha-voipms/commit/9905cacec03757af7bed7cb41b2d0e8335db93b6))
* **sms:** satisfy hassfest and stabilize logbook entity selection ([0639a97](https://github.com/andrewtryder/ha-voipms/commit/0639a9702470b4b034eddc7d1cc9950beabf6f1a))

## [1.3.2](https://github.com/andrewtryder/ha-voipms/compare/v1.3.1...v1.3.2) (2026-06-24)


### Bug Fixes

* **release:** sync manifest version and rename integration to VoIP.MS ([6f5b920](https://github.com/andrewtryder/ha-voipms/commit/6f5b92063c70e8c6b212ff55c6100c934a1d9ea9))
* **release:** sync manifest version and rename integration to VoIP.MS ([17f183c](https://github.com/andrewtryder/ha-voipms/commit/17f183ca9824243e214c7b199b7c58f8292b5866))

## [1.3.1](https://github.com/andrewtryder/ha-voipms/compare/v1.3.0...v1.3.1) (2026-06-24)


### Bug Fixes

* **webhook:** allow GET and register VoIP.ms SMS callback URL ([ddb5d7f](https://github.com/andrewtryder/ha-voipms/commit/ddb5d7fb783857f2702450ad44f23fe61e132df6))
* **webhook:** allow GET and register VoIP.ms SMS callback URL ([2cb6088](https://github.com/andrewtryder/ha-voipms/commit/2cb6088fce4233b293dc351cb43f3639b2fbbca3))

## [1.3.0](https://github.com/andrewtryder/ha-voipms/compare/v1.2.0...v1.3.0) (2026-06-24)


### Features

* **config:** improve setup auth diagnostics and troubleshooting ([25b29a0](https://github.com/andrewtryder/ha-voipms/commit/25b29a0b33914e73257fc452936c00778ecac868))
* **config:** improve setup auth diagnostics and troubleshooting ([93fdbd1](https://github.com/andrewtryder/ha-voipms/commit/93fdbd12c06567b5564a5d2708326324223c4de3))

## [1.2.0](https://github.com/andrewtryder/ha-voipms/compare/v1.1.0...v1.2.0) (2026-06-24)


### Features

* **docs:** update README for HACS integration ([72a2373](https://github.com/andrewtryder/ha-voipms/commit/72a237381189ba9d90c53370ae2b2335c39732aa))

## [1.1.0](https://github.com/andrewtryder/ha-voipms/compare/v1.0.0...v1.1.0) (2026-06-24)


### Features

* **docs:** update README for HACS integration ([fe732df](https://github.com/andrewtryder/ha-voipms/commit/fe732df7fb5ef6465439ba5207b9dcb79ab7128a))

## 1.0.0 (2026-06-24)


### Features

* add VoIP.ms brand assets for HACS and README ([de8921c](https://github.com/andrewtryder/ha-voipms/commit/de8921cae7c7a060057bd599d16fd070f3e451b7))
* Add VoIP.ms Custom Integration ([a01c792](https://github.com/andrewtryder/ha-voipms/commit/a01c792a7ea902ee6c19ffe44daf851bbb7863f0))
* Add VoIP.ms Custom Integration ([60ad9ff](https://github.com/andrewtryder/ha-voipms/commit/60ad9ffd1fdcdd577b0bcd40d8e323226bc35c79))
* **brand:** add asset tooling and local dev polish ([7bb4a4b](https://github.com/andrewtryder/ha-voipms/commit/7bb4a4b7ccaefc5116e3fbc75e0c3f336c3a03bb))
* **brand:** add asset tooling and local dev polish ([c0f8bd2](https://github.com/andrewtryder/ha-voipms/commit/c0f8bd2b1d251dc214bf22a24e2efc0d401f25f8))


### Bug Fixes

* **ci:** pass hassfest and ruff format checks for PR [#2](https://github.com/andrewtryder/ha-voipms/issues/2) ([73cfccf](https://github.com/andrewtryder/ha-voipms/commit/73cfccf6ada81060660cfebab48747ca9db09c66))
* format tools/build_voipms_assets.py to pass ruff format check ([a831d61](https://github.com/andrewtryder/ha-voipms/commit/a831d615b0dd99bfc03e9c866c786a6a67993f16))
* Resolve CI Validation Failures ([34c17fa](https://github.com/andrewtryder/ha-voipms/commit/34c17fa7dafb0825fc7e09ea9a7cd9923ddb7f0a))
* Resolve CI Validation Failures 2 ([c572fe6](https://github.com/andrewtryder/ha-voipms/commit/c572fe6b34d080cdb4e92b0c6938f5276ec93039))
* Simplify hacs.json to minimum valid schema ([71112f9](https://github.com/andrewtryder/ha-voipms/commit/71112f9f075ae05bcc5a0215a8d9af0199bff8b5))
* **voipms:** resolve python-ci formatting and test failures ([a2b195e](https://github.com/andrewtryder/ha-voipms/commit/a2b195e4932233721fe61fde3890c915ef7d83e4))
