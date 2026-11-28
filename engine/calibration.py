"""Validate provided reference labels and measure selective classification.

Threshold exploration is calibration, never independent acceptance. A previously
inspected dataset cannot become unseen by splitting it retrospectively.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

THRESHOLDS = (0, .003, .005, .008, .01, .015, .02)
ABSTAIN = '__ABSTAIN__'


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('EMPTY_OR_INVALID_DATASET')
    seen, classes, prepared = set(), None, []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('INVALID_LABEL_ROW')
        sha = row.get('sha256')
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
            raise ValueError('INVALID_IMAGE_SHA256')
        if sha in seen:
            raise ValueError('DUPLICATE_IMAGE')
        seen.add(sha)
        scores = row.get('scores')
        if (not isinstance(scores, dict) or len(scores) < 2 or
                any(not isinstance(k, str) or not k or k == ABSTAIN or not _number(v) for k, v in scores.items())):
            raise ValueError('INVALID_CLASS_SCORES')
        current = set(scores)
        if classes is None:
            classes = current
        if current != classes or row.get('label') not in classes:
            raise ValueError('INCONSISTENT_CLASS_SCHEMA')
        ranked = sorted(scores, key=lambda label: (-scores[label], label))
        margin = scores[ranked[0]] - scores[ranked[1]]
        if 'margin' in row and (not _number(row['margin']) or not math.isclose(row['margin'], margin, rel_tol=1e-6, abs_tol=1e-8)):
            raise ValueError('MARGIN_SCORE_MISMATCH')
        prepared.append({**row, '_prediction': ranked[0], '_margin': margin, '_tie': margin == 0})
    return prepared, sorted(classes)


def evaluate(rows, threshold):
    if not _number(threshold) or threshold < 0:
        raise ValueError('INVALID_THRESHOLD')
    prepared, classes = validate_rows(rows)
    accepted = [r for r in prepared if not r['_tie'] and r['_margin'] >= threshold]
    accepted_shas = {r['sha256'] for r in accepted}
    correct = sum(r['_prediction'] == r['label'] for r in accepted)
    confusion = {label: {prediction: 0 for prediction in classes + [ABSTAIN]} for label in classes}
    for row in prepared:
        prediction = row['_prediction'] if row['sha256'] in accepted_shas else ABSTAIN
        confusion[row['label']][prediction] += 1
    per_class = {}
    for label in classes:
        actual = [r for r in prepared if r['label'] == label]
        predicted = [r for r in accepted if r['_prediction'] == label]
        tp = confusion[label][label]
        accepted_support = sum(r['label'] == label for r in accepted)
        per_class[label] = {
            'support': len(actual), 'predicted': len(predicted), 'true_positive': tp,
            'false_positive': len(predicted) - tp, 'false_negative': len(actual) - tp,
            'abstained': confusion[label][ABSTAIN], 'accepted_support': accepted_support,
            'coverage': accepted_support / len(actual) if actual else None,
            'precision': tp / len(predicted) if predicted else None,
            'recall': tp / len(actual) if actual else None,
            'f1': 2 * tp / (len(predicted) + len(actual)) if actual else None,
            'recall_given_accepted': tp / accepted_support if accepted_support else None}
    precisions = [r['precision'] for r in per_class.values() if r['precision'] is not None]
    recalls = [r['recall'] for r in per_class.values() if r['recall'] is not None]
    f1_scores = [r['f1'] for r in per_class.values() if r['f1'] is not None]
    class_coverages = [r['coverage'] for r in per_class.values() if r['coverage'] is not None]
    return {'per_class': per_class,
            'missing_classes': [k for k, v in per_class.items() if not v['support']],
            'threshold': threshold, 'total': len(rows), 'accepted': len(accepted), 'correct': correct,
            'abstained': len(rows) - len(accepted), 'ties': sum(r['_tie'] for r in prepared),
            'false_accepts': len(accepted) - correct,
            'coverage': len(accepted) / len(rows),
            'selective_accuracy': correct / len(accepted) if accepted else None,
            'selective_error_rate': (len(accepted) - correct) / len(accepted) if accepted else None,
            'correct_fraction_of_all': correct / len(rows),
            'macro_precision': sum(precisions) / len(precisions) if precisions else None,
            'macro_recall': sum(recalls) / len(recalls) if recalls else None,
            'macro_f1': sum(f1_scores) / len(f1_scores) if f1_scores else None,
            'macro_f1_classes': [label for label in classes if per_class[label]['support']],
            'balanced_coverage': sum(class_coverages) / len(class_coverages) if class_coverages else None,
            'human_review_status': 'UNVERIFIED', 'acceptance_qualified': False,
            'confusion_matrix': confusion, 'commercial_approved': False}


def dataset_sha256(rows):
    # Includes labels, scores and grouping; input order cannot change identity.
    ordered = sorted(rows, key=lambda row: row['sha256'])
    raw = json.dumps(ordered, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _source_key(url):
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            raise ValueError('INVALID_SOURCE_URL')
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid', 'igshid')]
        return urlunsplit(('https', parts.netloc.lower(), parts.path.rstrip('/'), urlencode(sorted(query)), ''))
    except ValueError as exc:
        raise ValueError('INVALID_SOURCE_URL') from exc


def _groups(rows, group_key):
    """Union explicit product/near-duplicate groups and shared source pages."""
    parent = {row['sha256']: row['sha256'] for row in rows}
    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    def union(a, b):
        first, second = sorted((find(a), find(b)))
        parent[second] = first
    groups, sources = {}, {}
    for row in rows:
        group = row.get(group_key)
        if not isinstance(group, str) or not group.strip():
            raise ValueError('GROUP_METADATA_REQUIRED')
        sha = row['sha256']
        if group in groups:
            union(sha, groups[group])
        groups[group] = sha
        source = _source_key(row.get('source_url'))
        if source:
            if source in sources:
                union(sha, sources[source])
            sources[source] = sha
    components = {}
    for sha in sorted(parent):
        components.setdefault(find(sha), []).append(sha)
    return list(components.values())


def create_split(rows, *, acceptance_fraction=.25, seed='mhvie-calibration-v1',
                 group_key='group_id', frozen_threshold=None, previously_inspected=True):
    validate_rows(rows)
    if (not _number(acceptance_fraction) or not 0 < acceptance_fraction < 1 or
            not isinstance(seed, str) or not seed):
        raise ValueError('INVALID_SPLIT_CONFIGURATION')
    if frozen_threshold is not None and (not _number(frozen_threshold) or frozen_threshold < 0):
        raise ValueError('INVALID_THRESHOLD')
    groups = _groups(rows, group_key)
    if len(groups) < 2:
        raise ValueError('INSUFFICIENT_INDEPENDENT_GROUPS')
    groups.sort(key=lambda group: hashlib.sha256((seed + ':' + ','.join(group)).encode()).hexdigest())
    acceptance_count = min(len(groups) - 1, max(1, round(len(groups) * acceptance_fraction)))
    assignments = {sha: ('acceptance' if i < acceptance_count else 'calibration')
                   for i, group in enumerate(groups) for sha in group}
    return {'schema_version': 1, 'dataset_sha256': dataset_sha256(rows), 'seed': seed,
            'group_key': group_key, 'independent_groups': len(groups),
            'requested_acceptance_fraction': acceptance_fraction,
            'frozen_threshold': frozen_threshold, 'previously_inspected': bool(previously_inspected),
            'independent_acceptance_eligible': not previously_inspected,
            'human_review_status': 'UNVERIFIED', 'acceptance_qualified': False,
            'assignments': assignments}


def evaluate_split(rows, manifest, split='calibration', thresholds=THRESHOLDS):
    validate_rows(rows)
    if split not in ('calibration', 'acceptance') or manifest.get('schema_version') != 1:
        raise ValueError('INVALID_SPLIT_PROTOCOL')
    if manifest.get('dataset_sha256') != dataset_sha256(rows):
        raise ValueError('DATASET_CHANGED')
    assignments = manifest.get('assignments', {})
    if set(assignments) != {row['sha256'] for row in rows} or any(value not in ('calibration', 'acceptance') for value in assignments.values()):
        raise ValueError('INVALID_SPLIT_ASSIGNMENTS')
    for group in _groups(rows, manifest.get('group_key', 'group_id')):
        if len({assignments[sha] for sha in group}) != 1:
            raise ValueError('GROUP_OR_SOURCE_LEAKAGE')
    if split == 'acceptance':
        if manifest.get('previously_inspected') is not False or manifest.get('independent_acceptance_eligible') is not True:
            raise ValueError('PREVIOUSLY_INSPECTED_DATA_NOT_INDEPENDENT_ACCEPTANCE')
        if manifest.get('frozen_threshold') is None:
            raise ValueError('FROZEN_THRESHOLD_REQUIRED')
        thresholds = [manifest['frozen_threshold']]
    selected = [row for row in rows if assignments[row['sha256']] == split]
    if not selected:
        raise ValueError('EMPTY_SPLIT')
    return {'split': split, 'dataset_sha256': manifest['dataset_sha256'],
            'independent_acceptance': split == 'acceptance',
            'human_review_status': 'UNVERIFIED', 'acceptance_qualified': False,
            'results': [evaluate(selected, threshold) for threshold in thresholds]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('labels')
    parser.add_argument('--create-split', type=Path)
    parser.add_argument('--split-manifest', type=Path)
    parser.add_argument('--split', choices=('calibration', 'acceptance'), default='calibration')
    parser.add_argument('--threshold', type=float)
    parser.add_argument('--new-unseen-dataset', action='store_true', help='Explicit declaration only; does not make previously viewed images unseen')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = Path(args.labels).read_bytes()
    rows = json.loads(source)
    validate_rows(rows)
    if args.create_split and args.split_manifest:
        parser.error('choose --create-split or --split-manifest')
    manifest = None
    if args.create_split:
        manifest = create_split(rows, frozen_threshold=args.threshold,
                                previously_inspected=not args.new_unseen_dataset)
        args.create_split.write_text(json.dumps(manifest, indent=2) + '\n')
    if args.split_manifest:
        manifest = json.loads(args.split_manifest.read_text())
    if manifest is not None:
        report = evaluate_split(rows, manifest, args.split,
                                [args.threshold] if args.threshold is not None else THRESHOLDS)
    else:
        if args.split == 'acceptance':
            parser.error('acceptance requires --split-manifest and its frozen threshold')
        report = {'split': 'exploratory_calibration', 'independent_acceptance': False,
                  'results': [evaluate(rows, t) for t in ([args.threshold] if args.threshold is not None else THRESHOLDS)]}
    report['human_review_status'] = 'UNVERIFIED'
    report['acceptance_qualified'] = False
    report['source_file_sha256'] = hashlib.sha256(source).hexdigest()
    output = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(output)
    print(output, end='')


if __name__ == '__main__':
    main()
