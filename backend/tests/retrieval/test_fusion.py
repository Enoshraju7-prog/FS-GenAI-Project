from uuid import uuid4

from app.retrieval.fusion import reciprocal_rank_fusion


def test_chunk_ranked_in_both_lists_scores_higher_than_single_list():
    shared = uuid4()
    only_semantic = uuid4()
    only_fts = uuid4()

    fused = reciprocal_rank_fusion([[shared, only_semantic], [shared, only_fts]])
    fused_ids = [chunk_id for chunk_id, _ in fused]

    assert fused_ids[0] == shared
    scores = dict(fused)
    assert scores[shared] > scores[only_semantic]
    assert scores[shared] > scores[only_fts]


def test_result_order_matches_rrf_formula():
    a, b, c = uuid4(), uuid4(), uuid4()
    # a: rank 1 in both lists, b: rank 2 in both, c: only in one list at rank 1
    fused = reciprocal_rank_fusion([[a, b], [a, b, c]], k=60)
    scores = dict(fused)

    assert scores[a] == 1 / 61 + 1 / 61
    assert scores[b] == 1 / 62 + 1 / 62
    assert scores[c] == 1 / 63
    assert [chunk_id for chunk_id, _ in fused] == [a, b, c]


def test_empty_rankings_return_empty_list():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_one_empty_leg_falls_back_to_the_other():
    a, b = uuid4(), uuid4()
    fused = reciprocal_rank_fusion([[a, b], []])

    assert [chunk_id for chunk_id, _ in fused] == [a, b]
