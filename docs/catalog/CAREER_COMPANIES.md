# Career-page company inventory

Updated: 09 November 2026.

**378 company/display-name entries** configured in the career-page pipeline. Multiple boards or student feeds for the same display name share one row; separate divisions may retain their own display names.

This is a configuration inventory, not a live health check, a count of companies with current jobs, or a guarantee of complete descriptions. It excludes the separate URL-reader pipeline.

Compiled from `backend/config/sources.py`, `backend/config/career_expansion.py`, `backend/config/career_targets_20261030.py`, `backend/config/career_discovered.py`, `backend/config/career_browser_20261102.py`, `backend/config/display.py`, and every registered collector in `backend/core/collector.py`.

Regenerate offline after source changes: `runtime/python/Scripts/python.exe -m scripts.career.company_inventory`. This command does not collect jobs or change the database.

The older `COMPANY_SOURCES.json` is a curated 75-company audit input, not the full inventory. Dated observations are in [Source maintenance](../SOURCE_STATUS.md); the [26 October expansion](CAREER_EXPANSION_20261026.md) and [30 October target check](CAREER_EXPANSION_20261030.md), and the [2 November discovery notes](CAREER_DISCOVERY.md) record validation scope, unresolved companies and salary uncertainty.

| Company | Configuration key / board | Source / collector |
|---|---|---|
| 3M | `threem` | `workday_india` |
| 6sense | `6sense` | `greenhouse` |
| Abnormal AI | `abnormalsecurity` | `greenhouse` |
| Acceldata | `acceldata` | `lever` |
| Accenture | `accenture` | `workday_india` |
| Acko | `acko` | `employer_portals / kula` |
| Adobe | `adobe` | `phenom` |
| Agoda | `agoda` | `greenhouse` |
| Airbnb | `airbnb` | `greenhouse` |
| Airbus | `airbus` | `workday_india` |
| Akamai Technologies | `akamai` | `employer_portals / oracle` |
| AlphaGrep | `alphagrepsecurities` | `greenhouse` |
| Alteryx | `alteryx` | `workday_india` |
| Amadeus Labs | `amadeus` | `workday_india` |
| Amagi | `amagi` | `workable` |
| Amazon | `amazon` | `amazon (dedicated adapter)` |
| AMD | `amd` | `amd (dedicated adapter)` |
| American Express | `amex` | `oracle` |
| Ameriprise Financial | `ameriprise` | `workday_india` |
| Analog Devices | `analogdevices` | `workday_india` |
| Anaplan | `anaplan` | `greenhouse` |
| Anthropic | `anthropic` | `greenhouse` |
| ANZ | `anz` | `employer_portals / successfactors` |
| Aon | `aon` | `employer_portals / jibe` |
| Apollo Global Management | `apollo` | `workday_india` |
| Appian | `appian` | `greenhouse` |
| Apple | `apple` | `apple (dedicated adapter)` |
| Applied Materials | `amat` | `workday_india` |
| Aptiv | `aptiv` | `workday_india` |
| AQR Capital Management | `aqr` | `greenhouse` |
| Arcesium | `arcesiumllc` | `greenhouse` |
| Arista Networks | `AristaNetworks` | `smartrecruiters` |
| Atlan | `atlan` | `ashby` |
| Atlassian | `atlassian` | `atlassian (dedicated adapter)` |
| Autodesk | `autodesk` | `workday` |
| Automattic | `automattic` | `automattic (dedicated adapter)` |
| Axtria | `axtria` | `axtria (dedicated adapter)` |
| Baker Hughes | `bakerhughes` | `workday_india` |
| Bank Of America | `bank_of_america` | `bank_of_america (dedicated adapter)` |
| Barclays | `barclays` | `barclays (dedicated adapter)` |
| Barracuda | `barracuda` | `barracuda (dedicated adapter)` |
| Beghou Consulting | `beghouconsulting` | `lever` |
| BitGo | `bitgo` | `greenhouse` |
| BlackRock | `blackrock` | `blackrock (dedicated adapter)` |
| Blackstone | `blackstone` | `workday_india` |
| Bloomberg | `bloomberg` | `bloomberg (dedicated adapter)` |
| BMC Software | `bmcsoftware` | `bmcsoftware (dedicated adapter)` |
| BNY | `bny` | `employer_portals / oracle` |
| Boeing | `boeing` | `workday_india` |
| Booking.com | `booking` | `booking (dedicated adapter)` |
| Boomi | `boomilp` | `greenhouse` |
| Bosch | `BoschGroup` | `smartrecruiters` |
| Boston Consulting Group | `bcg` | `phenom` |
| bp | `bp` | `workday_india` |
| Bristol Myers Squibb | `bms` | `workday_india` |
| Broadcom | `broadcom` | `workday_india` |
| Broadridge | `broadridge` | `workday_india` |
| BrowserStack | `browserstack` | `workday_india` |
| C5i | `c5i` | `employer_portals / c5i` |
| Cadence Design Systems | `cadence` | `workday_india` |
| Capgemini | `capgemini` | `employer_portals / capgemini` |
| Capital One | `capitalone` | `workday_india` |
| Cars24 | `cars24` | `smartrecruiters` |
| Cashfree Payments | `cashfree` | `employer_portals / kula` |
| Celigo | `celigo` | `greenhouse` |
| Ciena | `ciena` | `workday_india` |
| Cigna | `cigna` | `workday_india` |
| Cisco | `cisco` | `workday` |
| Citi | `citi` | `workday_india` |
| Clarivate | `clarivate` | `workday_india` |
| Clear (ClearTax) | `cleartax` | `employer_portals / darwinbox` |
| Clearwater Analytics | `clearwater` | `greenhouse` |
| CleverTap | `clevertap` | `employer_portals / kula` |
| ClickHouse | `clickhouse` | `ashby` |
| Cloudera | `cloudera` | `workday_india` |
| Cloudflare | `cloudflare` | `greenhouse` |
| CME Group | `cmegroup` | `workday_india` |
| Cognite | `cognite` | `greenhouse` |
| Cohesity | `cohesity` | `workday_india` |
| Coinbase | `coinbase` | `greenhouse` |
| Commvault | `commvault` | `greenhouse` |
| Confluent | `confluent` | `ashby` |
| ConnectWise | `connectwise` | `greenhouse` |
| Couchbase | `couchbaseinc` | `greenhouse` |
| Coupa | `coupa` | `lever` |
| Coursera | `coursera` | `greenhouse` |
| CRED | `cred` | `lever` |
| CrowdStrike | `crowdstrike` | `workday_india` |
| Cummins | `cummins` | `employer_portals / oracle` |
| Cvent | `cvent` | `icims` |
| D. E. Shaw India | `deshaw` | `deshaw (dedicated adapter)` |
| Danaher | `danaher` | `workday_india` |
| Darwinbox | `darwinbox` | `employer_portals / darwinbox` |
| Databricks | `databricks` | `greenhouse` |
| Datadog | `datadog` | `greenhouse` |
| DataWeave | `dataweave` | `employer_portals / dataweave` |
| DBS Bank | `dbs` | `workday_india` |
| Delhivery | `delhivery` | `employer_portals / darwinbox` |
| Deliveroo | `deliveroo` | `greenhouse` |
| Dell | `dell` | `oracle` |
| Deloitte | `deloitte` | `deloitte (dedicated adapter)` |
| Delphi Consulting | `delphiconsulting` | `greenhouse` |
| Deutsche Bank | `deutsche_bank` | `deutsche_bank (dedicated adapter)` |
| Dialpad | `dialpad` | `greenhouse` |
| Druva | `druva` | `greenhouse` |
| Dun & Bradstreet | `dnb` | `lever` |
| Duolingo | `duolingo` | `greenhouse` |
| Eaton | `eaton` | `eightfold` |
| Eightfold AI | `eightfoldai` | `employer_portals / pcsx` |
| Elastic | `elastic` | `greenhouse` |
| Electronic Arts | `ea` | `ea (dedicated adapter)` |
| ElevenLabs | `elevenlabs` | `ashby` |
| Epsilon | `epsilon` | `employer_portals / jibe` |
| Ericsson | `ericsson` | `eightfold` |
| Evalueserve | `evalueserve` | `employer_portals / darwinbox` |
| EXL | `exl` | `oracle` |
| Experian India | `Experian` | `smartrecruiters` |
| Extreme Networks | `extremenetworks` | `lever` |
| ExxonMobil | `exxonmobil` | `employer_portals / successfactors` |
| F5 | `f5` | `workday_india` |
| FactSet | `factset` | `workday_india` |
| Fampay | `fampay` | `lever` |
| Fanatics Betting & Gaming | `fanaticsfbg` | `greenhouse` |
| Fanatics Collectibles | `fanaticscollectibles` | `greenhouse` |
| Fanatics Commerce | `fanaticscommerce` | `greenhouse` |
| Fanatics Corporate | `fanaticsinc` | `greenhouse` |
| Fi Money | `epifi` | `lever` |
| FICO | `fico` | `workday_india` |
| Fidelity International | `fidelity` | `workday` |
| Fidelity Investments | `fidelityinvestments` | `workday_india` |
| Figma | `figma` | `greenhouse` |
| Finastra | `finastra` | `workday_india` |
| FIS | `fis` | `workday_india` |
| Fiserv | `fiserv` | `phenom` |
| Fivetran | `fivetran` | `greenhouse` |
| Flipkart | `flipkart` | `flipkart (dedicated adapter)` |
| FNZ | `fnz` | `workday_india` |
| Fractal Analytics | `fractal` | `workday` |
| Freshworks | `Freshworks` | `smartrecruiters` |
| Gainsight | `gainsight` | `ashby` |
| Gartner | `gartner` | `workday_india` |
| GE Aerospace | `geaerospace` | `workday_india` |
| GE Appliances | `geappliances` | `workday_india` |
| Gen Digital | `gen-digital` | `ashby` |
| Genesys | `genesys` | `workday_india` |
| Genpact | `genpact` | `workday_india` |
| GitLab | `gitlab` | `greenhouse` |
| Glean | `gleanwork` | `greenhouse` |
| Global Payments | `globalpayments` | `workday_india` |
| Goldman Sachs | `goldman_sachs` | `goldman_sachs (dedicated adapter)` |
| Google | `google` | `google_careers` |
| Graviton Research Capital LLP | `gravitonresearchcapital` | `greenhouse` |
| Groww | `groww` | `greenhouse` |
| GSK | `gsk` | `workday_india` |
| Guidewire | `guidewire` | `workday_india` |
| HackerRank | `hackerrank` | `greenhouse` |
| Harness | `harnessinc` | `greenhouse` |
| HCLTech | `hcltech` | `successfactors` |
| Hevo Data | `hevodata` | `lever` |
| Hewlett Packard Enterprise | `hpe` | `workday_india` |
| Hexaware | `hexaware` | `employer_portals / oracle` |
| HighRadius | `highradius` | `greenhouse` |
| Honeywell | `honeywell` | `employer_portals / oracle` |
| HP | `hp` | `workday` |
| HSBC | `hsbc` | `hsbc (dedicated adapter)` |
| IBM | `ibm` | `ibm (dedicated adapter)` |
| Icertis | `icertis` | `employer_portals / oracle` |
| IMC | `imc` | `greenhouse` |
| IndiaMART | `indiamart` | `indiamart` |
| Info Edge | `infoedge` | `infoedge (dedicated adapter)` |
| InMobi | `inmobi` | `greenhouse` |
| Innovaccer | `innovaccer-analytics` | `workable` |
| Intel | `intel` | `workday` |
| Intercontinental Exchange | `ice` | `employer_portals / jibe` |
| Intuit | `intuit` | `intuit (dedicated adapter)` |
| Invesco | `invesco` | `workday_india` |
| ION Group | `ion` | `lever` |
| IQVIA | `iqvia` | `workday_india` |
| JFrog | `jfrog` | `greenhouse` |
| Josh Technology Group | `joshtechnologygroup` | `joshtechnologygroup (dedicated adapter)` |
| JPMorgan Chase | `jpmc` | `oracle` |
| Jumio | `jumio` | `greenhouse` |
| Jump Trading | `jumptrading` | `greenhouse` |
| Jupiter Money | `jupiter` | `employer_portals / keka` |
| Juspay | `juspay` | `juspay (dedicated adapter)` |
| Kissht | `kissht` | `employer_portals / kissht` |
| KLA | `kla` | `workday_india` |
| Kore.ai | `koreai` | `smartrecruiters` |
| KPMG Global Services | `kpmg` | `employer_portals / oracle` |
| LatentView Analytics | `latentview` | `employer_portals / darwinbox` |
| LeadSquared | `leadsquared` | `employer_portals / darwinbox` |
| Lenskart | `lenskart` | `ainterviews` |
| LinkedIn | `linkedin_company` | `linkedin_company (dedicated adapter)` |
| Lowe's India | `lowes` | `lowes (dedicated adapter)` |
| LSEG | `lseg` | `workday_india` |
| Macquarie | `macquarie` | `employer_portals / avature` |
| MakeMyTrip | `makemytrip` | `makemytrip (dedicated adapter)` |
| Manhattan Associates | `manh` | `workday_india` |
| MAQ Software | `maqsoftware` | `maqsoftware (dedicated adapter)` |
| Marsh McLennan | `marsh` | `phenom` |
| Marvell Technology | `marvell` | `workday_india` |
| Mastercard | `mastercard` | `mastercard_workday (dedicated adapter)`, `phenom` |
| MathCo | `mathco` | `employer_portals / peoplestrong` |
| MathWorks | `mathworks` | `mathworks (dedicated adapter)` |
| McKinsey & Company | `mckinsey` | `employer_portals / mckinsey` |
| MediaTek | `mediatek` | `mediatek (dedicated adapter)` |
| Medpace | `medpace` | `employer_portals / jibe` |
| Medtronic | `medtronic` | `workday` |
| Meesho | `meesho` | `lever` |
| Meta | `meta` | `meta (dedicated adapter)` |
| Microchip Technology | `microchip` | `workday_india` |
| Micron Technology | `micron` | `micron (dedicated adapter)` |
| Microsoft | `microsoft` | `eightfold` |
| Millennium | `millennium` | `millennium (dedicated adapter)` |
| Mindtickle | `mindtickle` | `lever` |
| Mixpanel | `mixpanel` | `greenhouse` |
| MoEngage | `moengage` | `employer_portals / trakstar` |
| Moneyview | `moneyview` | `employer_portals / darwinbox` |
| MongoDB | `mongodb` | `greenhouse` |
| Moody's | `moodys` | `employer_portals / talentbrew` |
| Morgan Stanley | `morganstanley` | `eightfold`, `morgan_stanley_students (dedicated adapter)` |
| Morningstar | `morningstar` | `workday_india` |
| MUFG | `mufg` | `workday_india` |
| Myntra | `myntra` | `myntra (dedicated adapter)` |
| Narvar | `narvar` | `greenhouse` |
| Nasdaq | `nasdaq` | `workday_india` |
| NatWest Group | `natwest` | `workday_india` |
| Navi | `navi` | `ashby` |
| NCR Voyix | `ncrvoyix` | `workday` |
| NetApp | `netapp` | `netapp (dedicated adapter)` |
| Netflix | `netflix` | `netflix (dedicated adapter)` |
| Netomi | `netomi` | `lever` |
| Netradyne | `Netradyne` | `smartrecruiters` |
| Netskope | `netskope` | `greenhouse` |
| New Relic | `newrelic` | `greenhouse` |
| Newton School | `newtonschool` | `smartrecruiters` |
| Nielsen | `TheNielsenCompany` | `smartrecruiters` |
| NielsenIQ | `NielsenIQ` | `smartrecruiters` |
| Ninjacart | `ninjacart` | `employer_portals / darwinbox` |
| Nium | `nium` | `lever` |
| NK Securities Research | `nksecuritiesresearch` | `greenhouse` |
| Nokia India | `nokia` | `employer_portals / oracle` |
| Nomura | `nomura` | `successfactors` |
| Northern Trust | `northerntrust` | `workday_india` |
| Notion | `notion` | `ashby` |
| Novartis | `novartis` | `workday_india` |
| Nutanix | `nutanix` | `nutanix (dedicated adapter)` |
| NVIDIA | `nvidia` | `workday` |
| NXP Semiconductors | `nxp` | `workday_india` |
| o9 Solutions | `o9solutions` | `workday_india` |
| Observe.AI | `observeai` | `greenhouse` |
| Okta | `okta` | `greenhouse` |
| OneTrust | `onetrust` | `greenhouse` |
| Open Financial Technologies | `openfinancial` | `employer_portals / keka` |
| Openai | `openai` | `ashby` |
| Optiver | `optiverus` | `greenhouse` |
| Oracle / OCI | `oracle` | `oracle` |
| Palo Alto Networks | `paloaltonetworks` | `workday` |
| PayPal | `paypal` | `paypal (dedicated adapter)` |
| Paytm | `paytm` | `lever` |
| PayU | `payu` | `successfactors` |
| Perfios | `perfios` | `employer_portals / darwinbox` |
| PharmEasy | `pharmeasy` | `employer_portals / darwinbox` |
| Philips | `philips` | `workday_india` |
| PhonePe | `PHONEPELIMITED` | `smartrecruiters` |
| Pocket FM | `pocketfm` | `lever` |
| Portcast | `portcast` | `lever` |
| Porter | `porter` | `employer_portals / darwinbox` |
| Postman | `postman` | `workday_india` |
| PromptQL (Hasura) | `hasura` | `employer_portals / gem` |
| Proofpoint | `proofpoint` | `workday_india` |
| Prudential Financial | `prudential` | `workday_india` |
| Publicis Sapient | `publicissapient` | `publicissapient (dedicated adapter)` |
| PubMatic | `pubmatic` | `greenhouse` |
| Pure Storage | `purestorage` | `greenhouse` |
| PwC India | `pwc` | `pwc (dedicated adapter)` |
| Q2 | `q2ebanking` | `workday_india` |
| Qlik | `qlik` | `employer_portals / pcsx` |
| Quadeye | `quadeye` | `quadeye (dedicated adapter)` |
| Quantiphi | `quantiphi` | `workday_india` |
| Qube Research & Technologies | `quberesearchandtechnologies` | `greenhouse` |
| Razorpay | `razorpaysoftwareprivatelimited` | `greenhouse` |
| Red Hat | `redhat` | `workday_india` |
| Renesas Electronics | `RenesasElectronics` | `smartrecruiters` |
| RingCentral | `ringcentral` | `workday_india` |
| Rippling | `rippling` | `rippling (dedicated adapter)` |
| Rocketlane | `rocketlane` | `employer_portals / kula` |
| Rockwell Automation | `rockwell` | `workday_india` |
| Roku | `roku` | `greenhouse` |
| Rubrik | `rubrik` | `greenhouse` |
| S&P Global | `spglobal` | `icims` |
| Sabre | `sabre` | `workday_india` |
| Salesforce | `salesforce` | `workday` |
| Samsara | `samsara` | `greenhouse` |
| Samsung | `samsung` | `workday` |
| SAP Labs India | `sap` | `sap (dedicated adapter)` |
| Sarvam | `sarvam` | `ashby` |
| Scaler | `interviewbit` | `smartrecruiters` |
| Schneider Electric | `schneiderelectric` | `employer_portals / jibe` |
| ServiceNow | `servicenow` | `smartrecruiters` |
| Shell | `shell` | `workday_india` |
| Siemens Digital Industries Software | `siemenssoftware` | `siemenssoftware (dedicated adapter)` |
| Siemens Healthineers | `siemenshealthineers` | `workday_india` |
| Sigmoid Analytics | `sigmoid` | `greenhouse` |
| Signzy | `signzy` | `employer_portals / keka` |
| Silicon Labs | `silabs` | `workday_india` |
| SingleStore | `singlestore` | `greenhouse` |
| Slice | `slice` | `employer_portals / kula` |
| Smarsh | `smarsh` | `lever` |
| Snowflake | `snowflake` | `ashby` |
| Sophos | `sophos` | `lever` |
| Spinny | `spinny` | `employer_portals / darwinbox` |
| Sprinklr | `sprinklr` | `workday` |
| Sprinto | `Sprinto` | `lever` |
| Squarepoint Capital | `squarepointcapital` | `greenhouse` |
| Standard Chartered | `standardchartered` | `successfactors` |
| Starburst | `starburst` | `greenhouse` |
| State Street | `statestreet` | `workday_india` |
| Stripe | `stripe` | `greenhouse` |
| Sumo Logic | `sumologic` | `greenhouse` |
| Swiggy | `swiggy` | `swiggy (dedicated adapter)` |
| Swiss Re | `swissre` | `swissre (dedicated adapter)` |
| Synopsys | `synopsys` | `employer_portals / talentbrew` |
| Target | `target` | `target (dedicated adapter)` |
| Tekion | `tekion` | `ashby` |
| Teradata | `teradata` | `teradata (dedicated adapter)` |
| Tesco | `tesco` | `tesco (dedicated adapter)` |
| Texas Instruments India | `texasinstruments` | `employer_portals / oracle` |
| Thales | `thales` | `workday_india` |
| Thomson Reuters | `thomsonreuters` | `workday_india` |
| ThoughtSpot | `thoughtspot` | `workday_india` |
| Thoughtworks | `thoughtworks` | `greenhouse` |
| Tiger Analytics | `tiger-analytics` | `workable` |
| Toast | `toast` | `greenhouse` |
| Tower Research Capital | `towerresearchcapital` | `tower_research (dedicated adapter)` |
| TransUnion (India group) | `transunion` | `workday_india` |
| Tredence Analytics | `tredence` | `tredence (dedicated adapter)` |
| Trellix | `trellix` | `workday_india` |
| Trimble | `trimble` | `workday_india` |
| Turing | `turing` | `greenhouse` |
| Twilio | `twilio` | `greenhouse` |
| Typeface | `typeface` | `greenhouse` |
| Uber | `uber` | `uber (dedicated adapter)` |
| UBS | `ubs` | `ubs (dedicated adapter)` |
| UiPath | `uipath` | `ashby` |
| Ukg | `ukg` | `eightfold` |
| Unacademy | `unacademy` | `smartrecruiters` |
| Uniphore | `uniphore` | `workday_india` |
| United Airlines | `unitedairlines` | `employer_portals / unitedairlines` |
| UnitedHealth Group / Optum | `unitedhealthgroup` | `unitedhealthgroup (dedicated adapter)` |
| Upstox | `upstox` | `employer_portals / upstox` |
| Urban Company | `urbancompany` | `employer_portals / urbancompany` |
| Vanguard | `vanguard` | `workday_india` |
| Veeva Systems | `veeva` | `lever` |
| Vercel | `vercel` | `greenhouse` |
| Visa | `visa` | `workday`, `workday_students` |
| Vodafone Idea | `vodafoneidea` | `successfactors` |
| Walmart Global Tech | `walmart` | `workday`, `workday_students` |
| WebEngage | `webengage` | `employer_portals / keka` |
| Wells Fargo | `wellsfargo` | `workday_india` |
| Western Digital | `WesternDigital` | `smartrecruiters` |
| Whatfix | `whatfix` | `employer_portals / trakstar` |
| Wingify | `wingify` | `employer_portals / keka` |
| Wolters Kluwer | `wolterskluwer` | `workday_india` |
| Workday | `workdaycompany` | `workday_india` |
| WorldQuant | `worldquant` | `greenhouse` |
| YipitData | `yipitdatajobs` | `greenhouse` |
| Yugabyte | `yugabyte` | `greenhouse` |
| Zendesk | `zendesk` | `workday_india` |
| Zenoti | `zenoti` | `greenhouse` |
| Zepto | `zepto` | `zepto (dedicated adapter)` |
| Zerodha | `zerodha` | `zerodha (dedicated adapter)` |
| Zeta | `zeta` | `lever` |
| Zoom | `zoom` | `workday_india` |
| ZoomInfo | `zoominfo` | `greenhouse` |
| ZS Associates | `zs` | `zs (dedicated adapter)` |
| Zscaler | `zscaler` | `greenhouse` |
| Zuora | `zuora` | `greenhouse` |

## Disabled sources

Excluded from the active count and collection. Existing saved records and exports are retained.

| Company | Source | Reason |
|---|---|---|
| Expedia Group | [expedia](https://careers.expediagroup.com/jobs/?filter%5Bcountry%5D=India) | Disabled 27 October 2026: HTTP 403; earlier HTTP 429 rate limiting. |
| Hudson River Trading | [hrt](https://www.hudsonrivertrading.com/careers/?locations=mumbai%2C) | Disabled 27 October 2026: HTTP 403 access challenge. |
| Qualcomm | [qualcomm](https://careers.qualcomm.com/careers?location=India) | Disabled 8 November 2026: HTTP 405 from AWS WAF human verification (CAPTCHA) on /api/pcsx/search; covers the main India feed and the Intern-only qualcomm_students collector. |
