# Contributing to Conduction

Welkom bij de codebase van Conduction! We waarderen je bijdragen en hanteren een aantal richtlijnen om samenwerking soepel te laten verlopen. Lees dit document goed door voordat je een pull request (PR) indient.

## 🚀 Hoe Bijdragen

1. **Issues Checken**
   - Controleer of er al een bestaand issue is voor je verandering.
   - Als je een nieuw issue aanmaakt, gebruik de juiste labels en duidelijke titels.

2. **Werken met Git & Branches**
   - Gebruik altijd feature branches (`feature/naam-van-feature`)
   - Bugfixes op `bugfix/naam-van-bug`
   - Release branches worden beheerd door de tech lead.

3. **Code Standaarden**
   - Houd je aan **PSR-2** coding style.
   - Documenteer code met **DocBlock** commentaar.
   - Gebruik linting tools zoals ESLint en PHP-CS-Fixer waar nodig.

4. **Pull Requests (PRs)**
   - Zorg dat je code werkt vóór je een PR indient.
   - Voeg een beschrijving toe en link relevante issues.
   - Laat minimaal één teamlid een review doen.
   - Geen PR’s direct naar `main`! Gebruik `develop` als staging branch.

5. **Tests & Kwaliteit**
   - Schrijf unit tests voor nieuwe functionaliteit.
   - Code coverage moet minimaal **80%** zijn.
   - Gebruik **Jest** voor frontend tests en **PHPUnit** voor backend tests.

6. **Beveiliging & Gevoelige Data**
   - **NOOIT** API keys, wachtwoorden of tokens in de repo pushen.
   - Zorg dat `.env` bestanden **niet** worden gecommit.
   - Volg de beveiligingsrichtlijnen in `TEAM_MANIFESTO.md`.

## 🔗 Verdere Documentatie

- **Team werkafspraken & proces:** Zie [`TEAM_MANIFESTO.md`](TEAM_MANIFESTO.md)
- **Scrum & dagelijkse workflow:** Zie [`WORK_AGREEMENTS.md`](WORK_AGREEMENTS.md)

Bedankt voor je bijdrage! 🚀
