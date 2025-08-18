# Changelog

All notable changes to the Suite from version **3.0** onward will be documented here, categorized into **Added**, **Changed**, **Fixed**, and **Removed**.

Each entry includes a reference to the related Jira ticket or issue number (e.g., BMK-XXXX).

---

## [v3.1] – Released 14 Aug 2025

### Added
- **Suite:** [BMK-1685] Adapted run script to HEPScore v2.0 logic
- **Suite:** [BMK-1685] Adjustable n-cores and HEPscore version validation
- **Suite:** [BMK-1712] Added threadscan functionality and fixed supported hepscore versions 
- **Suite:** [BMK-1722] Allow by default to test plugins with BMK* branches
- **Suite:** [BMK-1731] Created Changelog file to track notable changes. 
- **Suite:** [BMK-1742] Added config option and long argument names


### Changed
- **Plugins:** [BMK-1464]: Metadata extraction now happens before the benchmark run
- **Suite:** [BMK-1713] Make less scaring the message in run_piped_commands
- **BMK-Run:** [BMK-1736] Changing default for --mode/-m in bmkrun


### Fixed
- **Plugins:** [BMK-1655] Updated power-consumption plugin : fixed additional backslashes
- **Suite:** [BMK-1714] Ensuring proper termination of _run_benchmark
- **Suite:** [BMK-1710] Correct SELinux handling


### Removed
- *(Nothing removed yet.)*

---

## [v3.0] – Initial Release *(template/example only)*

*(The following entries are examples to demonstrate the changelog format.)*

### Added
- **Suite:** [BMK-XXXX] Description of a new feature. 
- **RunScript:** [BMK-XXXX] Introduced new flag: `-ZXY`. 

### Changed
- **Refactor:** [BMK-XXXX] Improved performance of function `X`. 
- **RunScript:** [BMK-XXXX] Modified behavior of component `XY`. 
- **Suite (MyFunction):** [BMK-XXXX] Updated interface for clarity. 

### Fixed
- **Bug:** [BMK-XXXX] Fixed crash occurring under condition `X`. 
- **UI:** [BMK-XXXX] Corrected misleading log message. 

### Removed
- **Legacy:** [BMK-XXXX] Deprecated functionality `XY`. 
- **Feature:** [BMK-XXXX] Dropped support for outdated component. 

---
