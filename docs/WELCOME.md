# 👋 Welcome — Advanced Tracing Workshop

## While you get settled, install these tools:

Participants inspect Braintrust with `bt` in the terminal. Instructors will cover the Braintrust UI, but participant interactions will stay in terminal. 

### 1. Braintrust CLI (`bt`)

```bash
curl -fsSL https://bt.dev/cli/install.sh | bash
```

Verify install

```bash
bt --version
```

### 2. `uv` (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify install

```bash
uv --version
```

### 3. Clone the workshop repo

```bash
git clone https://github.com/imhurl23/advanced-tracing-workshop.git
cd advanced-tracing-workshop
make setup
```

Continue with [Participant Guide, step 2](PARTICIPANT.md#2-configure) to fill in `.env`.
