# coding: utf-8

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.gui.howl_change import HowlChange

BANKS = HowlCollection.BANKS
SONGS = HowlCollection.SONGS


class TestTouches:

    def test_the_blob_that_changed(self):
        assert HowlChange(SONGS, 3).touches(SONGS, 3)

    def test_not_a_different_index(self):
        assert not HowlChange(SONGS, 3).touches(SONGS, 4)

    def test_not_the_other_collection(self):
        assert not HowlChange(SONGS, 3).touches(BANKS, 3)

    def test_a_file_wide_change_touches_everything(self):
        assert HowlChange().touches(BANKS, 0)
        assert HowlChange().touches(SONGS, 99)

    def test_a_structural_change_touches_everything(self):
        """Removing song 3 renumbers every song after it, so a view showing
        song 9 is now showing something else."""
        assert HowlChange(SONGS, 3, structural=True).touches(SONGS, 9)


class TestMerging:
    """Replacing a sample shared by several banks pushes one command per bank,
    so the descriptors have to collapse into one update."""

    def test_two_edits_to_the_same_blob_stay_precise(self):
        merged = HowlChange(SONGS, 3, sub_index=1).merged_with(
            HowlChange(SONGS, 3, sub_index=1),
        )

        assert merged == HowlChange(SONGS, 3, sub_index=1)

    def test_different_sub_indices_widen_to_the_whole_blob(self):
        merged = HowlChange(SONGS, 3, sub_index=1).merged_with(
            HowlChange(SONGS, 3, sub_index=7),
        )

        assert merged == HowlChange(SONGS, 3)

    def test_different_blobs_widen_to_file_wide(self):
        merged = HowlChange(BANKS, 1).merged_with(HowlChange(BANKS, 4))

        assert merged.is_file_wide

    def test_structural_survives_the_merge(self):
        merged = HowlChange(BANKS, 1).merged_with(HowlChange(BANKS, 4, structural=True))

        assert merged.structural

    def test_merging_is_not_lossy_about_reach(self):
        """Whatever either side touched, the merge must touch too."""
        merged = HowlChange(BANKS, 1).merged_with(HowlChange(SONGS, 2))

        assert merged.touches(BANKS, 1)
        assert merged.touches(SONGS, 2)
