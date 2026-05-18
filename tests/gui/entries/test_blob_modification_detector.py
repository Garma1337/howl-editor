# coding: utf-8


class TestModifiedIndices:

    def test_returns_empty_when_no_original(self, blob_modification_detector):
        result = blob_modification_detector.modified_indices([b"a", b"b"], None)

        assert result == set()

    def test_returns_empty_when_all_match(self, blob_modification_detector):
        current = [b"a", b"b", b"c"]
        original = [b"a", b"b", b"c"]

        assert blob_modification_detector.modified_indices(current, original) == set()

    def test_detects_changed_blob(self, blob_modification_detector):
        current = [b"a", b"X", b"c"]
        original = [b"a", b"b", b"c"]

        assert blob_modification_detector.modified_indices(current, original) == {1}

    def test_appended_blobs_are_modified(self, blob_modification_detector):
        current = [b"a", b"b", b"c", b"d"]
        original = [b"a", b"b"]

        assert blob_modification_detector.modified_indices(current, original) == {2, 3}

    def test_combination(self, blob_modification_detector):
        current = [b"X", b"b", b"Y", b"d"]
        original = [b"a", b"b", b"c"]

        assert blob_modification_detector.modified_indices(current, original) == {0, 2, 3}


class TestIsModified:

    def test_false_when_no_original(self, blob_modification_detector):
        assert blob_modification_detector.is_modified([b"a"], None, 0) is False

    def test_false_for_unchanged(self, blob_modification_detector):
        assert blob_modification_detector.is_modified([b"a"], [b"a"], 0) is False

    def test_true_for_changed(self, blob_modification_detector):
        assert blob_modification_detector.is_modified([b"X"], [b"a"], 0) is True

    def test_true_for_appended(self, blob_modification_detector):
        assert blob_modification_detector.is_modified([b"a", b"b"], [b"a"], 1) is True

    def test_false_for_out_of_range(self, blob_modification_detector):
        assert blob_modification_detector.is_modified([b"a"], [b"a"], 5) is False
        assert blob_modification_detector.is_modified([b"a"], [b"a"], -1) is False
