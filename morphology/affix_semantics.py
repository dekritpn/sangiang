"""Affix Semantic Catalogue and Morphological Rules for Bahasa Sangihe.

Defines the systematic semantic shift rules for Sangihe affixes:
- Prefixes (ma-, me-, manga-, maka-, paka-, ipa-, ka-, etc.)
- Infixes (-um-, -in-, -im-)
- Suffixes (-ang, -eng)
- Circumfixes (ka-...-ang, pe-...-ang, etc.)
- Reduplications (full & partial)
- Morphophonemic mutations (b <-> w, d <-> r, nasal assimilation)
"""

from typing import Dict, List, Optional, Tuple


AFFIX_SEMANTIC_RULES: Dict[str, Dict[str, str]] = {
    # 1. INFIXES (SISIPAN DALAM PERUT KATA)
    "-um-": {
        "name": "Sisipan Aktif / Fokus Pelaku (Actor Focus)",
        "position": "infix",
        "description": "Diselipkan di antara konsonan pertama dan vokal pertama. Mengubah kata dasar nomina/adjektiva/verba menjadi tindakan aktif yang sedang berlangsung.",
        "semantic_effect": "Menyatakan tindakan aktif, gerakan, atau pelaku yang sedang melakukan perbuatan.",
        "example_root": "dal᷊eng (jalan)",
        "example_derived": "dumal᷊eng (sedang berjalan, melangkah)",
    },
    "-in-": {
        "name": "Sisipan Realis / Aspek Selesai (Perfective / Past)",
        "position": "infix",
        "description": "Diselipkan di antara konsonan pertama dan vokal pertama. Mengubah kata dasar menjadi bentuk peristiwa yang telah benar-benar terjadi atau fokus penderita/pasien.",
        "semantic_effect": "Menyatakan aspek lampau, pekerjaan yang telah rampung, atau keadaan yang telah dialami.",
        "example_root": "kaěng (makan/makanan)",
        "example_derived": "kimaěng (telah makan / menyantap)",
    },

    # 2. PREFIXES (AWALAN)
    "ma-": {
        "name": "Awalan Keadaan / Sifat / Verba Statif",
        "position": "prefix",
        "description": "Melekat pada kata dasar sifat atau benda. Kerap memicu alih bunyi b -> w pada konsonan bibir.",
        "semantic_effect": "Menyatakan keadaan memiliki sifat tersebut, menjadi, atau berada dalam kondisi tertentu.",
        "example_root": "baesẹ̌ (sarang / kemarau)",
        "example_derived": "mawaesẹ̌ (menjadi kering / reda dari hujan)",
    },
    "mě-": {
        "name": "Awalan Verba Aktif / Berdiam / Menetap",
        "position": "prefix",
        "description": "Melekat pada kata dasar nomina atau verba dengan vokal pepet e.",
        "semantic_effect": "Menyatakan perbuatan berdiam, menempati, atau melakukan aktivitas yang berkaitan dengan kata dasar.",
        "example_root": "baesẹ̌ (sarang / tempat kediaman)",
        "example_derived": "měbaesẹ̌ (bersarang / bertempat tinggal)",
    },
    "manga-": {
        "name": "Awalan Verba Aktif Transitif / Jamak",
        "position": "prefix",
        "description": "Awalan aktif yang menunjukkan pekerjaan terhadap objek atau kegiatan jamak/berulang.",
        "semantic_effect": "Menyatakan aktivitas aktif yang dilakukan secara sengaja atau berulang-ulang.",
        "example_root": "abasẹ̌ (tantangan / kesombongan)",
        "example_derived": "mangabasẹ̌ (menantang dengan congkak / membual)",
    },
    "maka-": {
        "name": "Awalan Potensial / Kesanggupan / Tak Sengaja",
        "position": "prefix",
        "description": "Melekat pada kata kerja untuk menandai kemampuan atau hasil akhir.",
        "semantic_effect": "Menyatakan kesanggupan ('dapat/berhasil melakukan') atau kejadian spontan/tak sengaja.",
        "example_root": "silo (lihat)",
        "example_derived": "makasilo (berhasil melihat / dapat melihat)",
    },
    "naka-": {
        "name": "Awalan Potensial Selesai (Past Potential)",
        "position": "prefix",
        "description": "Bentuk lampau/realis dari maka-.",
        "semantic_effect": "Menyatakan bahwa pelaku telah berhasil atau telah sanggup menyelesaikan perbuatan.",
        "example_root": "silo (lihat)",
        "example_derived": "nakasilo (telah berhasil melihat)",
    },
    "paka-": {
        "name": "Awalan Kausatif / Pengintensif (Intensifier / Causative)",
        "position": "prefix",
        "description": "Melekat pada kata sifat untuk membentuk perintah atau anjuran bersikap.",
        "semantic_effect": "Menyatakan 'buatlah menjadi' atau 'secara sungguh-sungguh/hati-hati'.",
        "example_root": "ingatẹ̌ (ingat / hati-hati)",
        "example_derived": "pakaingatẹ̌ (berhati-hatilah sungguh-sungguh)",
    },
    "ipang-": {
        "name": "Awalan Instrumen / Alat (Instrumental Focus)",
        "position": "prefix",
        "description": "Membentuk nomina atau verba fokus alat.",
        "semantic_effect": "Menyatakan alat, perkakas, atau sarana yang digunakan untuk melakukan perbuatan.",
        "example_root": "darisẹ̌ (gores / garis)",
        "example_derived": "ipandarisẹ̌ (alat yang dipakai untuk menggores)",
    },
    "ka-": {
        "name": "Awalan Nomina Abstrak / Derajat Sifat",
        "position": "prefix",
        "description": "Melekat pada kata sifat atau nomina.",
        "semantic_effect": "Menyatakan perihal sifat tersebut, atau tingkatan derajat.",
        "example_root": "těngadẹ̌ (benar / sungguh)",
        "example_derived": "katěngadẹ̌ (kebenaran / kesungguhan)",
    },

    # 3. CIRCUMFIXES (KONFIKS)
    "ka-...-ang": {
        "name": "Konfiks Tempat / Wadah / Kumpulan / Konsep Abstrak",
        "position": "circumfix",
        "description": "Mengapit kata dasar di awal dan akhir.",
        "semantic_effect": "Menyatakan tempat kedudukan, daerah kekuasaan, atau kumpulan yang terkait dengan kata dasar.",
        "example_root": "datu (raja / penguasa)",
        "example_derived": "kadatuang (wilayah kerajaan / takhta pemerintahan)",
    },
    "pe-...-ang": {
        "name": "Konfiks Lokatif Aktivitas (Activity Location)",
        "position": "circumfix",
        "description": "Mengapit kata kerja untuk membentuk nomina tempat berkegiatan.",
        "semantic_effect": "Menyatakan tempat atau waktu berlangsungnya pekerjaan tersebut.",
        "example_root": "tatikilang (tidur / berbaring)",
        "example_derived": "pẹ̌tatikilang (kamar tidur / tempat berbaring)",
    },

    # 4. SUFFIXES (AKHIRAN)
    "-ang": {
        "name": "Akhiran Lokatif / Penerima (Locative / Recipient Focus)",
        "position": "suffix",
        "description": "Melekat di akhir kata dasar.",
        "semantic_effect": "Menandai lokasi arah atau pihak yang dikenai pekerjaan.",
        "example_root": "tul᷊ung (tolong)",
        "example_derived": "tul᷊ungang (tolonglah / tempat memohon bantuan)",
    },
    "-eng": {
        "name": "Akhiran Pasien / Sasaran (Patient Focus)",
        "position": "suffix",
        "description": "Melekat di akhir kata dasar untuk membentuk fokus sasaran langsung.",
        "semantic_effect": "Menyatakan benda atau objek yang langsung menjadi sasaran tindakan.",
        "example_root": "kaěng (makan)",
        "example_derived": "kanengang (hal/makanan yang akan disantap)",
    },
}


def explain_affix_logic(affix_symbol: str) -> Optional[Dict[str, str]]:
    """Return the detailed morphological and semantic logic for a given affix symbol."""
    return AFFIX_SEMANTIC_RULES.get(affix_symbol)
