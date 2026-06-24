# Contributing to Retail Analyst

First off, thank you for considering contributing to Retail Analyst! It's people like you that make the open-source community such a great place to learn, inspire, and create.

## 1. Branch Strategy
We follow a standard Git Flow branching model:
- `main` - The production-ready branch.
- `develop` - The active development branch.
- `feature/*` - For new features (e.g., `feature/add-recharts`).
- `bugfix/*` - For bug fixes (e.g., `bugfix/fix-sql-generator`).

## 2. Commit Conventions
We use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` A new feature.
- `fix:` A bug fix.
- `docs:` Documentation only changes.
- `style:` Changes that do not affect the meaning of the code (white-space, formatting).
- `refactor:` A code change that neither fixes a bug nor adds a feature.
- `test:` Adding missing tests or correcting existing tests.

Example: `feat: add auto-healing SQL loop to backend`

## 3. Pull Request Workflow
1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'feat: add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request against the `develop` branch.
6. Ensure CI/CD GitHub Actions pass.

## 4. Coding Standards
- **Python**: Follow PEP 8 guidelines. Use type hints wherever possible.
- **Frontend**: Use functional React components and TypeScript strict mode. Ensure proper use of CSS variables for theming.
- Ensure no sensitive information (API keys, DB credentials) is committed to version control.
