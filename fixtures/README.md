# Gitto Synthetic Finance Dataset Generator

This directory contains a comprehensive synthetic finance dataset generator for testing and development of the Gitto platform.

## Overview

The generator creates realistic test data including:
- **AR Invoices**: Open and paid invoices with customer/country/terms, including edge cases
- **AP Vendor Bills**: Bills with approval/hold states and payment run scheduling
- **Bank Statements**: Multiple formats (CSV, MT940, BAI2, camt.053 ISO 20022)
- **FX Rates**: Weekly rates with intentional missing-rate gaps
- **Multi-Entity**: Multiple entities with intercompany transfers

## Usage

```bash
python fixtures/generate_synthetic_data.py
```

This will generate all datasets in the `fixtures/` directory.

## Generated Files

### Core Datasets

- **`entities.csv`**: Multi-entity structure (3 entities: US, EU, UK)
- **`ar_invoices.csv`**: AR invoices with open/paid history, credit notes, rebills, partials
- **`ap_vendor_bills.csv`**: AP vendor bills with approval/hold states
- **`fx_rates.csv`**: FX rates per week (13 weeks) with intentional gaps
- **`bank_transactions.csv`**: Bank transactions in CSV format

### Bank Statement Formats

- **`bank_statements.mt940`**: SWIFT MT940 format
- **`bank_statements.bai2`**: BAI2 format
- **`bank_statements_camt053.xml`**: camt.053 (ISO 20022) XML format

### Metadata

- **`manifest.json`**: Complete manifest describing all datasets, invariants, and known exceptions

## Edge Cases Included

The generator includes configurable edge cases to test data quality handling:

- **Duplicates** (2%): Duplicate document numbers
- **Credit Notes** (5%): Negative amount invoices linked to parent invoices
- **Rebills** (3%): Reissued invoices
- **Partial Payments** (10%): Partial payment records
- **Noisy References** (15%): Bank transaction references with variations/noise
- **Blank Fields** (5%): Merged-cell-like blank fields (country, project)
- **Scientific Notation** (1%): Amounts in scientific notation (Excel export edge case)
- **Missing FX Rates** (8%): Intentional gaps in FX rate data

## Configuration

Edge case rates can be configured in the `EdgeCaseConfig` class:

```python
edge_config = EdgeCaseConfig(
    duplicate_rate=0.02,
    credit_note_rate=0.05,
    rebill_rate=0.03,
    partial_payment_rate=0.10,
    noisy_reference_rate=0.15,
    blank_field_rate=0.05,
    scientific_notation_rate=0.01,
    missing_fx_rate=0.08
)
```

## Data Invariants

The manifest.json documents expected invariants:

1. All invoices have entity_id matching an entity
2. All vendor bills have entity_id matching an entity
3. Credit notes have negative amounts
4. Partial payments sum to less than or equal to parent invoice amount
5. Intercompany transfers are marked with is_wash=1
6. Bank transactions match invoice amounts (within tolerance) when reconciled
7. FX rates are positive numbers
8. Payment dates are after invoice dates
9. Due dates are after invoice dates

## Known Exceptions

The manifest.json also documents known exceptions (intentional edge cases):

- Blank fields in invoices (simulates Excel merged cells)
- Scientific notation amounts (Excel export edge case)
- Duplicate document numbers (data quality issues)
- Noisy bank references (real-world variations)
- Missing FX rates (data gaps)
- Intercompany transfers appearing in both entities (expected behavior)

## Data Volume

Default generation creates:
- 3 entities
- ~700 AR invoices (including credit notes, rebills, partials)
- ~450 AP vendor bills
- ~940 bank transactions
- ~71 FX rate records (with gaps)
- Intercompany transfers between entities

## Format Details

### MT940 Format
SWIFT MT940 standard format with:
- Statement header (`:20:`, `:25:`, `:28C:`)
- Transaction entries (`:61:`, `:86:`)
- Statement footer (`:62F:`)

### BAI2 Format
Bank Administration Institute BAI2 format with:
- File header (`01`)
- Account header (`02`)
- Transaction detail (`16`, `88`)
- Account trailer (`49`)
- File trailer (`99`)

### camt.053 Format
ISO 20022 camt.053 XML format with:
- Document structure
- Group header
- Statement with account details
- Balance information
- Transaction entries with remittance information

## Testing

These datasets are designed for:
- Testing reconciliation matching algorithms
- Validating edge case handling
- Testing multi-entity scenarios
- Testing FX rate gap handling
- Testing intercompany netting
- Performance testing with realistic data volumes

## Regeneration

To regenerate datasets with different random seed:

```python
import random
random.seed(123)  # Change seed
generator = SyntheticDataGenerator()
generator.generate_all()
```

Or modify `RANDOM_SEED` in the script.


