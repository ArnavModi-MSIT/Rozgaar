# Career-page company inventory

Updated: 26 October 2026.

**286 company/display-name entries** configured in the career-page pipeline. Multiple boards or student feeds for the same display name share one row; separate divisions may retain their own display names.

This is a configuration inventory, not a live health check, a count of companies with current jobs, or a guarantee of complete descriptions. It excludes the separate URL-reader pipeline.

Compiled from `backend/config/sources.py`, `backend/config/career_expansion.py`, `backend/config/display.py`, and every registered collector in `backend/core/collector.py`.

Regenerate offline after source changes: `runtime/python/Scripts/python.exe -m scripts.career.company_inventory`. This command does not collect jobs or change the database.

The older `COMPANY_SOURCES.json` is a curated 75-company audit input, not the full inventory. Dated observations are in [Source maintenance](../SOURCE_STATUS.md); the [26 October expansion](CAREER_EXPANSION_20261026.md) records validation scope and salary uncertainty.

| Company | Configuration key / board | Source / collector |
|---|---|---|
| 6sense | `6sense` | `greenhouse` |
| Abnormal AI | `abnormalsecurity` | `greenhouse` |
| Acceldata | `acceldata` | `lever` |
| Accenture | `accenture` | `workday_india` |
| Acko | `acko` | `employer_portals / kula` |
| Adobe | `adobe` | `phenom` |
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
| Analog Devices | `analogdevices` | `workday_india` |
| Anthropic | `anthropic` | `greenhouse` |
| ANZ | `anz` | `employer_portals / successfactors` |
| Apollo Global Management | `apollo` | `workday_india` |
| Appian | `appian` | `greenhouse` |
| Apple | `apple` | `apple (dedicated adapter)` |
| Applied Materials | `amat` | `workday_india` |
| Aptiv | `aptiv` | `workday_india` |
| AQR Capital Management | `aqr` | `greenhouse` |
| Arcesium | `arcesiumllc` | `greenhouse` |
| Arista Networks | `AristaNetworks` | `smartrecruiters` |
| Atlassian | `atlassian` | `atlassian (dedicated adapter)` |
| Autodesk | `autodesk` | `workday` |
| Automattic | `automattic` | `automattic (dedicated adapter)` |
| Baker Hughes | `bakerhughes` | `workday_india` |
| Bank Of America | `bank_of_america` | `bank_of_america (dedicated adapter)` |
| Barclays | `barclays` | `barclays (dedicated adapter)` |
| BitGo | `bitgo` | `greenhouse` |
| BlackRock | `blackrock` | `blackrock (dedicated adapter)` |
| Blackstone | `blackstone` | `workday_india` |
| Bloomberg | `bloomberg` | `bloomberg (dedicated adapter)` |
| BNY | `bny` | `employer_portals / oracle` |
| Boeing | `boeing` | `workday_india` |
| Booking.com | `booking` | `booking (dedicated adapter)` |
| Bosch | `BoschGroup` | `smartrecruiters` |
| Boston Consulting Group | `bcg` | `phenom` |
| Bristol Myers Squibb | `bms` | `workday_india` |
| Broadcom | `broadcom` | `workday_india` |
| Broadridge | `broadridge` | `workday_india` |
| BrowserStack | `browserstack` | `workday_india` |
| C5i | `c5i` | `employer_portals / c5i` |
| Cadence Design Systems | `cadence` | `workday_india` |
| Capital One | `capitalone` | `workday_india` |
| Cashfree Payments | `cashfree` | `employer_portals / kula` |
| Celigo | `celigo` | `greenhouse` |
| Ciena | `ciena` | `workday_india` |
| Cisco | `cisco` | `workday` |
| Citi | `citi` | `workday_india` |
| CleverTap | `clevertap` | `employer_portals / kula` |
| ClickHouse | `clickhouse` | `ashby` |
| Cloudera | `cloudera` | `workday_india` |
| Cloudflare | `cloudflare` | `greenhouse` |
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
| Cvent | `cvent` | `icims` |
| D. E. Shaw India | `deshaw` | `deshaw (dedicated adapter)` |
| Databricks | `databricks` | `greenhouse` |
| Datadog | `datadog` | `greenhouse` |
| DBS Bank | `dbs` | `workday_india` |
| Deliveroo | `deliveroo` | `greenhouse` |
| Dell | `dell` | `oracle` |
| Deloitte | `deloitte` | `deloitte (dedicated adapter)` |
| Deutsche Bank | `deutsche_bank` | `deutsche_bank (dedicated adapter)` |
| Dialpad | `dialpad` | `greenhouse` |
| Druva | `druva` | `greenhouse` |
| Duolingo | `duolingo` | `greenhouse` |
| Eightfold AI | `eightfoldai` | `employer_portals / pcsx` |
| Elastic | `elastic` | `greenhouse` |
| Electronic Arts | `ea` | `ea (dedicated adapter)` |
| ElevenLabs | `elevenlabs` | `ashby` |
| Ericsson | `ericsson` | `eightfold` |
| Evalueserve | `evalueserve` | `employer_portals / darwinbox` |
| EXL | `exl` | `oracle` |
| Expedia Group | `expedia` | `expedia (dedicated adapter)` |
| ExxonMobil | `exxonmobil` | `employer_portals / successfactors` |
| F5 | `f5` | `workday_india` |
| FactSet | `factset` | `workday_india` |
| Fampay | `fampay` | `lever` |
| Fanatics Betting & Gaming | `fanaticsfbg` | `greenhouse` |
| Fanatics Collectibles | `fanaticscollectibles` | `greenhouse` |
| Fanatics Commerce | `fanaticscommerce` | `greenhouse` |
| Fanatics Corporate | `fanaticsinc` | `greenhouse` |
| Fi Money | `epifi` | `lever` |
| Fidelity International | `fidelity` | `workday` |
| Fidelity Investments | `fidelityinvestments` | `workday_india` |
| FIS | `fis` | `workday_india` |
| Fiserv | `fiserv` | `phenom` |
| Fivetran | `fivetran` | `greenhouse` |
| Flipkart | `flipkart` | `flipkart (dedicated adapter)` |
| FNZ | `fnz` | `workday_india` |
| Fractal Analytics | `fractal` | `workday` |
| Freshworks | `Freshworks` | `smartrecruiters` |
| Gartner | `gartner` | `workday_india` |
| GE Aerospace | `geaerospace` | `workday_india` |
| GE Appliances | `geappliances` | `workday_india` |
| GitLab | `gitlab` | `greenhouse` |
| Glean | `gleanwork` | `greenhouse` |
| Goldman Sachs | `goldman_sachs` | `goldman_sachs (dedicated adapter)` |
| Google | `google` | `google_careers` |
| Graviton Research Capital LLP | `gravitonresearchcapital` | `greenhouse` |
| Groww | `groww` | `greenhouse` |
| Guidewire | `guidewire` | `workday_india` |
| HackerRank | `hackerrank` | `greenhouse` |
| Harness | `harnessinc` | `greenhouse` |
| Hewlett Packard Enterprise | `hpe` | `workday_india` |
| HighRadius | `highradius` | `greenhouse` |
| Honeywell | `honeywell` | `employer_portals / oracle` |
| HP | `hp` | `workday` |
| HSBC | `hsbc` | `hsbc (dedicated adapter)` |
| Hudson River Trading | `hrt` | `hrt (dedicated adapter)` |
| IBM | `ibm` | `ibm (dedicated adapter)` |
| Icertis | `icertis` | `employer_portals / oracle` |
| IMC | `imc` | `greenhouse` |
| IndiaMART | `indiamart` | `indiamart` |
| Info Edge | `infoedge` | `infoedge (dedicated adapter)` |
| InMobi | `inmobi` | `greenhouse` |
| Innovaccer | `innovaccer-analytics` | `workable` |
| Intel | `intel` | `workday` |
| Intuit | `intuit` | `intuit (dedicated adapter)` |
| ION Group | `ion` | `lever` |
| IQVIA | `iqvia` | `workday_india` |
| JFrog | `jfrog` | `greenhouse` |
| Josh Technology Group | `joshtechnologygroup` | `joshtechnologygroup (dedicated adapter)` |
| JPMorgan Chase | `jpmc` | `oracle` |
| Jumio | `jumio` | `greenhouse` |
| Jupiter Money | `jupiter` | `employer_portals / keka` |
| Juspay | `juspay` | `juspay (dedicated adapter)` |
| KLA | `kla` | `workday_india` |
| LatentView Analytics | `latentview` | `employer_portals / darwinbox` |
| Lenskart | `lenskart` | `ainterviews` |
| LinkedIn | `linkedin_company` | `linkedin_company (dedicated adapter)` |
| Lowe's India | `lowes` | `lowes (dedicated adapter)` |
| LSEG | `lseg` | `workday_india` |
| MakeMyTrip | `makemytrip` | `makemytrip (dedicated adapter)` |
| Manhattan Associates | `manh` | `workday_india` |
| MAQ Software | `maqsoftware` | `maqsoftware (dedicated adapter)` |
| Marvell Technology | `marvell` | `workday_india` |
| Mastercard | `mastercard` | `mastercard_workday (dedicated adapter)`, `phenom` |
| MathCo | `mathco` | `employer_portals / peoplestrong` |
| MathWorks | `mathworks` | `mathworks (dedicated adapter)` |
| MediaTek | `mediatek` | `mediatek (dedicated adapter)` |
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
| MongoDB | `mongodb` | `greenhouse` |
| Morgan Stanley | `morganstanley` | `eightfold`, `morgan_stanley_students (dedicated adapter)` |
| Morningstar | `morningstar` | `workday_india` |
| Myntra | `myntra` | `myntra (dedicated adapter)` |
| Narvar | `narvar` | `greenhouse` |
| Nasdaq | `nasdaq` | `workday_india` |
| NatWest Group | `natwest` | `workday_india` |
| Navi | `navi` | `ashby` |
| NetApp | `netapp` | `netapp (dedicated adapter)` |
| Netflix | `netflix` | `netflix (dedicated adapter)` |
| Netomi | `netomi` | `lever` |
| Netradyne | `Netradyne` | `smartrecruiters` |
| Netskope | `netskope` | `greenhouse` |
| New Relic | `newrelic` | `greenhouse` |
| NielsenIQ | `NielsenIQ` | `smartrecruiters` |
| NK Securities Research | `nksecuritiesresearch` | `greenhouse` |
| Northern Trust | `northerntrust` | `workday_india` |
| Notion | `notion` | `ashby` |
| Nutanix | `nutanix` | `nutanix (dedicated adapter)` |
| NVIDIA | `nvidia` | `workday` |
| NXP Semiconductors | `nxp` | `workday_india` |
| Observe.AI | `observeai` | `greenhouse` |
| Okta | `okta` | `greenhouse` |
| OneTrust | `onetrust` | `greenhouse` |
| Openai | `openai` | `ashby` |
| Optiver | `optiverus` | `greenhouse` |
| Oracle / OCI | `oracle` | `oracle` |
| Palo Alto Networks | `paloaltonetworks` | `workday` |
| PayPal | `paypal` | `paypal (dedicated adapter)` |
| Paytm | `paytm` | `lever` |
| PayU | `payu` | `successfactors` |
| Perfios | `perfios` | `employer_portals / darwinbox` |
| PhonePe | `PHONEPELIMITED` | `smartrecruiters` |
| Portcast | `portcast` | `lever` |
| Porter | `porter` | `employer_portals / darwinbox` |
| Postman | `postman` | `workday_india` |
| PromptQL (Hasura) | `hasura` | `employer_portals / gem` |
| Proofpoint | `proofpoint` | `workday_india` |
| Publicis Sapient | `publicissapient` | `publicissapient (dedicated adapter)` |
| PubMatic | `pubmatic` | `greenhouse` |
| Pure Storage | `purestorage` | `greenhouse` |
| PwC India | `pwc` | `pwc (dedicated adapter)` |
| Q2 | `q2ebanking` | `workday_india` |
| Quadeye | `quadeye` | `quadeye (dedicated adapter)` |
| Qualcomm | `qualcomm` | `eightfold`, `qualcomm_students (dedicated adapter)` |
| Quantiphi | `quantiphi` | `workday_india` |
| Qube Research & Technologies | `quberesearchandtechnologies` | `greenhouse` |
| Razorpay | `razorpaysoftwareprivatelimited` | `greenhouse` |
| Red Hat | `redhat` | `workday_india` |
| Renesas Electronics | `RenesasElectronics` | `smartrecruiters` |
| RingCentral | `ringcentral` | `workday_india` |
| Rippling | `rippling` | `rippling (dedicated adapter)` |
| Roku | `roku` | `greenhouse` |
| Rubrik | `rubrik` | `greenhouse` |
| S&P Global | `spglobal` | `icims` |
| Salesforce | `salesforce` | `workday` |
| Samsara | `samsara` | `greenhouse` |
| Samsung | `samsung` | `workday` |
| SAP Labs India | `sap` | `sap (dedicated adapter)` |
| Sarvam | `sarvam` | `ashby` |
| ServiceNow | `servicenow` | `smartrecruiters` |
| Shell | `shell` | `workday_india` |
| Siemens Healthineers | `siemenshealthineers` | `workday_india` |
| Sigmoid Analytics | `sigmoid` | `greenhouse` |
| Silicon Labs | `silabs` | `workday_india` |
| SingleStore | `singlestore` | `greenhouse` |
| Slice | `slice` | `employer_portals / kula` |
| Smarsh | `smarsh` | `lever` |
| Snowflake | `snowflake` | `ashby` |
| Spinny | `spinny` | `employer_portals / darwinbox` |
| Sprinklr | `sprinklr` | `workday` |
| Squarepoint Capital | `squarepointcapital` | `greenhouse` |
| Standard Chartered | `standardchartered` | `successfactors` |
| Starburst | `starburst` | `greenhouse` |
| State Street | `statestreet` | `workday_india` |
| Stripe | `stripe` | `greenhouse` |
| Sumo Logic | `sumologic` | `greenhouse` |
| Swiggy | `swiggy` | `swiggy (dedicated adapter)` |
| Swiss Re | `swissre` | `swissre (dedicated adapter)` |
| Target | `target` | `target (dedicated adapter)` |
| Tekion | `tekion` | `ashby` |
| Tesco | `tesco` | `tesco (dedicated adapter)` |
| Thales | `thales` | `workday_india` |
| Thomson Reuters | `thomsonreuters` | `workday_india` |
| ThoughtSpot | `thoughtspot` | `workday_india` |
| Thoughtworks | `thoughtworks` | `greenhouse` |
| Tiger Analytics | `tiger-analytics` | `workable` |
| Toast | `toast` | `greenhouse` |
| Tower Research Capital | `towerresearchcapital` | `tower_research (dedicated adapter)` |
| Tredence Analytics | `tredence` | `tredence (dedicated adapter)` |
| Trimble | `trimble` | `workday_india` |
| Twilio | `twilio` | `greenhouse` |
| Typeface | `typeface` | `greenhouse` |
| Uber | `uber` | `uber (dedicated adapter)` |
| UBS | `ubs` | `ubs (dedicated adapter)` |
| UiPath | `uipath` | `ashby` |
| Ukg | `ukg` | `eightfold` |
| Uniphore | `uniphore` | `workday_india` |
| UnitedHealth Group / Optum | `unitedhealthgroup` | `unitedhealthgroup (dedicated adapter)` |
| Upstox | `upstox` | `employer_portals / upstox` |
| Veeva Systems | `veeva` | `lever` |
| Vercel | `vercel` | `greenhouse` |
| Visa | `visa` | `workday`, `workday_students` |
| Walmart Global Tech | `walmart` | `workday`, `workday_students` |
| Wells Fargo | `wellsfargo` | `workday_india` |
| Western Digital | `WesternDigital` | `smartrecruiters` |
| Whatfix | `whatfix` | `employer_portals / trakstar` |
| Wingify | `wingify` | `employer_portals / keka` |
| Workday | `workdaycompany` | `workday_india` |
| WorldQuant | `worldquant` | `greenhouse` |
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
