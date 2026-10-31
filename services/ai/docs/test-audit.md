# Auditoría de tests del slice

Las variantes parametrizadas se agrupan bajo su función original. La evaluación se excluyó de esta fase. La comprobación de duplicados en `test_ingest_survives_bad_files` se perdió al sustituir los datos reales por un PDF sintético; se ha recuperado con un PDF sintético en el test migrado.

| Test original | Estado | Test nuevo |
|---|---|---|
| `test_adapters.py::test_fake_embedder_dim` | migrado | `tests/test_adapters.py::test_fake_embedder_dim` |
| `test_adapters.py::test_fake_reranker_preserves_order_scores` | migrado | `tests/test_adapters.py::test_fake_reranker_preserves_order_scores` |
| `test_adapters.py::test_fake_llm_json_schema_shape` | migrado | `tests/test_adapters.py::test_fake_llm_json_schema_shape` |
| `test_adapters.py::test_config_swap_changes_ports` | migrado | `tests/test_adapters.py::test_config_swap_changes_ports` |
| `test_ask.py::test_ask_verified_answer` | migrado | `tests/test_ask.py::test_ask_verified_answer` |
| `test_ask.py::test_ask_llm_rejects` | migrado | `tests/test_ask.py::test_ask_llm_rejects` |
| `test_ask.py::test_ask_false_citation_rejected` | migrado | `tests/test_ask.py::test_ask_false_citation_rejected` |
| `test_chunking.py::test_extract_pdf_text_has_sections` | migrado | `tests/test_chunking.py::test_extract_pdf_text_has_sections` |
| `test_chunking.py::test_chunk_pdf_sections_and_ids` | migrado | `tests/test_chunking.py::test_chunk_pdf_sections_and_ids` |
| `test_chunking.py::test_chunk_pdf_skips_footer` | migrado | `tests/test_chunking.py::test_chunk_pdf_skips_footer` |
| `test_chunking.py::test_chunk_invoice_fields_and_lines` | migrado | `tests/test_chunking.py::test_chunk_invoice_fields_and_lines` |
| `test_eval.py::test_eval_metrics` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_acceptance_and_reference_substrings_do_not_prove_correctness` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_wrong_incomplete_or_unsupported_answer_to_answerable_question_is_failure` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_paraphrase_can_pass_with_bound_review` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_exact_answer_and_explicit_approved_evidence_can_pass_automatically` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_exact_oracle_never_passes_partial_numbers_units_or_extra_claims` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_expected_number_does_not_replace_correct_evidence` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_multisource_oracle_requires_every_evidence_group` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_live_missing_evidence_is_failure` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_fabricated_quote_fails_even_with_positive_review` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_answerability_is_separate` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_errors_are_never_successful_refusals` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_bad_gold_fails_closed` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_duplicate_and_empty_gold_fail` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_review_cannot_be_reused_after_answer_citation_or_gold_changes` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_draft_gold_blocks_final_accuracy_even_if_answer_passes` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_legacy_missing_citations_cannot_be_approved` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_historical_rescore_preserves_inputs_and_does_not_trust_old_counters` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_rescore_applies_review_without_rerunning_models` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_incomplete_review_is_rejected` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_small_sample_percentile_stays_in_observed_range` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_run_eval_records_errors_and_continues_without_counting_them_as_refusals` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_invalid_gold_is_rejected_before_inference` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_known_verifier_holes_never_become_evaluation_success` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_cli_never_reports_success_for_pending_or_failed_evaluation` | excluido a propósito (eval) | — |
| `test_evaluation_contract.py::test_unknown_result_schema_is_not_silently_treated_as_legacy` | excluido a propósito (eval) | — |
| `test_invoices.py::test_multi_field` | migrado | `tests/test_invoices.py::test_multi_field` |
| `test_invoices.py::test_absent_invoice_and_field_refuse` | migrado | `tests/test_invoices.py::test_absent_invoice_and_field_refuse` |
| `test_invoices.py::test_filter_and_sum` | migrado | `tests/test_invoices.py::test_filter_and_sum` |
| `test_invoices.py::test_filter_value_braces_and_null_op` | migrado | `tests/test_invoices.py::test_filter_value_braces_and_null_op` |
| `test_invoices.py::test_router` | migrado | `tests/test_invoices.py::test_router` |
| `test_round3_fixes.py::test_degree_followed_by_word` | migrado | `tests/test_round3_fixes.py::test_degree_followed_by_word` |
| `test_round3_fixes.py::test_bare_number_with_unit_in_chunk` | migrado | `tests/test_round3_fixes.py::test_bare_number_with_unit_in_chunk` |
| `test_round3_fixes.py::test_unit_change_still_rejected` | migrado | `tests/test_round3_fixes.py::test_unit_change_still_rejected` |
| `test_round3_fixes.py::test_celsius_kept` | migrado | `tests/test_round3_fixes.py::test_celsius_kept` |
| `test_round3_fixes.py::test_absent_number_rejected` | migrado | `tests/test_round3_fixes.py::test_absent_number_rejected` |
| `test_round3_fixes.py::test_invoice_header_chunk_has_issuer_and_taxid` | migrado | `tests/test_round3_fixes.py::test_invoice_header_chunk_has_issuer_and_taxid` |
| `test_round3_fixes.py::test_ingest_survives_bad_files` | migrado | `tests/test_round3_fixes.py::test_ingest_survives_bad_files` |
| `test_round3_fixes.py::test_question_guard_before_any_model` | migrado | `tests/test_round3_fixes.py::test_question_guard_before_any_model` |
| `test_store.py::test_upsert_and_search` | migrado | `tests/test_store.py::test_upsert_and_search` |
| `test_store.py::test_ingest_idempotent` | migrado | `tests/test_store.py::test_ingest_idempotent` |
