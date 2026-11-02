"""Version 1.01; formulas transcribed from the supplied reagent calculator."""
import math
from decimal import Decimal, ROUND_CEILING


def calculate(format, antibodies, mw_kda, oligomer=1, mw_basis='monomer'):
    if format not in ('BLI', 'SPR'):
        raise ValueError('Choose BLI or SPR.')
    if isinstance(antibodies, bool) or int(antibodies) != antibodies or antibodies <= 0:
        raise ValueError('Antibody count must be a positive integer.')
    if not math.isfinite(float(mw_kda)) or mw_kda <= 0:
        raise ValueError('A positive molecular weight is required.')
    if oligomer not in (1, 2, 3):
        raise ValueError('Confirm monomer, dimer, or trimer stoichiometry.')
    if mw_basis not in ('monomer', 'assembly'):
        raise ValueError('Confirm whether MW describes a monomer or the full assembly.')
    capacity, volume_ul, concentration_nm = (96, 4000, 250) if format == 'BLI' else (372, 2000, 1000)
    batches = (int(antibodies) + capacity - 1) // capacity
    effective = Decimal(str(mw_kda)) * (oligomer if mw_basis == 'monomer' else 1)
    # Workbook H40 / H15: MW(kDa) * nM * volume(uL) / 1,000,000.
    # The workbook already includes two runs; no second safety multiplier.
    needed = effective * concentration_nm * volume_ul * batches / Decimal(1000000)
    rounded = (needed / 100).to_integral_value(rounding=ROUND_CEILING) * 100
    return {'Format': format, 'Antibodies': int(antibodies), 'Capacity per batch': capacity,
            'Batches': batches, 'Runs included': 2, 'Effective assembly MW (kDa)': float(effective),
            'Required antigen (ug)': float(needed), 'Purchase target (ug)': int(rounded),
            'Formula source': 'Octet & Carterra Menu (4-26-24)!H40' if format == 'BLI' else 'Octet & Carterra Menu (4-26-24)!H15'}
