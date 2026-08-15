/* Namibian places, bundled so search works with no signal.
 *
 * A farmer setting up in a communal area has patchy data at best, and the previous
 * flow gave them a zoom-5 map of the whole country and asked them to find their own
 * farm on it. This list is the primary search path; an online geocoder is only ever
 * an extra. Coordinates are approximate settlement centres — good enough to fly the
 * map to, after which the farmer drops the pin exactly.
 *
 * [name, lat, lon, region]
 */
const PLACES = [
  // ── Khomas ──
  ["Windhoek", -22.5609, 17.0658, "Khomas"], ["Katutura", -22.5183, 17.0611, "Khomas"],
  ["Khomasdal", -22.5461, 17.0428, "Khomas"], ["Dordabis", -22.9667, 17.6833, "Khomas"],
  ["Groot Aub", -22.9500, 17.1667, "Khomas"], ["Brakwater", -22.4333, 17.0667, "Khomas"],
  ["Seeis", -22.4500, 17.7500, "Khomas"], ["Nina", -22.7500, 17.4500, "Khomas"],

  // ── Oshana ──
  ["Oshakati", -17.7883, 15.7044, "Oshana"], ["Ondangwa", -17.9167, 15.9667, "Oshana"],
  ["Ongwediva", -17.7833, 15.7667, "Oshana"], ["Uukwiyu", -17.8667, 15.8333, "Oshana"],
  ["Okatana", -17.7500, 15.7667, "Oshana"], ["Ompundja", -18.0167, 15.7167, "Oshana"],
  ["Okaku", -17.8500, 15.9000, "Oshana"], ["Uuvudhiya", -18.3000, 15.5500, "Oshana"],
  ["Eheke", -17.8000, 15.6000, "Oshana"], ["Okatjali", -17.8333, 15.6500, "Oshana"],

  // ── Ohangwena ──
  ["Eenhana", -17.4833, 16.3333, "Ohangwena"], ["Helao Nafidi", -17.3833, 15.9167, "Ohangwena"],
  ["Oshikango", -17.4000, 15.8833, "Ohangwena"], ["Ohangwena", -17.5833, 16.1667, "Ohangwena"],
  ["Okongo", -17.4000, 17.0333, "Ohangwena"], ["Omundaungilo", -17.3000, 16.7000, "Ohangwena"],
  ["Endola", -17.5500, 15.8500, "Ohangwena"], ["Ondobe", -17.5000, 16.0500, "Ohangwena"],
  ["Engela", -17.4333, 15.8833, "Ohangwena"], ["Epembe", -17.6167, 16.4833, "Ohangwena"],
  ["Omulonga", -17.4500, 15.7500, "Ohangwena"], ["Oshikunde", -17.5833, 16.8333, "Ohangwena"],

  // ── Omusati ──
  ["Outapi", -17.5028, 14.9861, "Omusati"], ["Oshikuku", -17.6167, 15.1500, "Omusati"],
  ["Ruacana", -17.4167, 14.3667, "Omusati"], ["Okahao", -17.8833, 15.0667, "Omusati"],
  ["Tsandi", -17.7167, 14.8833, "Omusati"], ["Onesi", -17.5333, 14.7000, "Omusati"],
  ["Ogongo", -17.6833, 15.0333, "Omusati"], ["Elim", -17.7500, 15.1000, "Omusati"],
  ["Anamulenge", -17.6000, 14.9000, "Omusati"], ["Etayi", -17.4000, 14.8000, "Omusati"],
  ["Ombalantu", -17.5000, 14.9833, "Omusati"], ["Otamanzi", -18.0500, 15.0000, "Omusati"],
  ["Okalongo", -17.4667, 15.2333, "Omusati"], ["Uukwaluudhi", -17.8000, 14.8000, "Omusati"],

  // ── Oshikoto ──
  ["Tsumeb", -19.2333, 17.7167, "Oshikoto"], ["Omuthiya", -18.3667, 16.5833, "Oshikoto"],
  ["Oniipa", -17.9167, 16.0500, "Oshikoto"], ["Onayena", -17.9500, 16.2500, "Oshikoto"],
  ["Okankolo", -18.1500, 16.4000, "Oshikoto"], ["Guinas", -19.2000, 17.4000, "Oshikoto"],
  ["Olukonda", -18.0333, 16.0167, "Oshikoto"], ["Eengodi", -18.2000, 16.8000, "Oshikoto"],
  ["Nehale lyaMpingana", -18.5000, 16.9000, "Oshikoto"], ["Okatope", -18.0000, 16.2000, "Oshikoto"],

  // ── Kunene ──
  ["Opuwo", -18.0607, 13.8400, "Kunene"], ["Khorixas", -20.3667, 14.9667, "Kunene"],
  ["Outjo", -20.1167, 16.1500, "Kunene"], ["Kamanjab", -19.6167, 14.8333, "Kunene"],
  ["Sesfontein", -19.1167, 13.6167, "Kunene"], ["Epupa", -17.0000, 13.2500, "Kunene"],
  ["Okanguati", -17.4667, 13.5833, "Kunene"], ["Etanga", -17.5500, 12.9500, "Kunene"],
  ["Warmquelle", -19.2000, 13.8000, "Kunene"], ["Fransfontein", -20.2000, 15.0167, "Kunene"],
  ["Otjitanda", -17.2000, 13.1000, "Kunene"],

  // ── Otjozondjupa ──
  ["Otjiwarongo", -20.4642, 16.6478, "Otjozondjupa"], ["Grootfontein", -19.5667, 18.1167, "Otjozondjupa"],
  ["Okahandja", -21.9833, 16.9167, "Otjozondjupa"], ["Otavi", -19.6500, 17.3333, "Otjozondjupa"],
  ["Tsumkwe", -19.5833, 20.5000, "Otjozondjupa"], ["Okakarara", -20.5833, 17.4333, "Otjozondjupa"],
  ["Coblenz", -20.0000, 17.0000, "Otjozondjupa"], ["Kombat", -19.7167, 17.7167, "Otjozondjupa"],
  ["Waterberg", -20.5000, 17.2333, "Otjozondjupa"], ["Summerdown", -21.6167, 18.4667, "Otjozondjupa"],

  // ── Omaheke ──
  ["Gobabis", -22.4500, 18.9667, "Omaheke"], ["Otjinene", -21.1500, 18.7333, "Omaheke"],
  ["Witvlei", -22.4000, 18.4833, "Omaheke"], ["Leonardville", -23.4833, 18.8000, "Omaheke"],
  ["Aminuis", -23.6667, 19.3500, "Omaheke"], ["Epukiro", -21.7000, 19.1000, "Omaheke"],
  ["Talismanis", -22.7000, 19.6000, "Omaheke"], ["Buitepos", -22.2833, 19.9833, "Omaheke"],
  ["Drimiopsis", -22.0333, 18.7000, "Omaheke"], ["Otjombinde", -21.5000, 19.8000, "Omaheke"],

  // ── Erongo ──
  ["Swakopmund", -22.6833, 14.5333, "Erongo"], ["Walvis Bay", -22.9575, 14.5053, "Erongo"],
  ["Usakos", -21.9833, 15.5833, "Erongo"], ["Karibib", -21.9333, 15.8500, "Erongo"],
  ["Omaruru", -21.4333, 15.9333, "Erongo"], ["Arandis", -22.4167, 14.9667, "Erongo"],
  ["Henties Bay", -22.1167, 14.2833, "Erongo"], ["Uis", -21.2333, 14.8667, "Erongo"],
  ["Spitzkoppe", -21.8333, 15.1833, "Erongo"], ["Okombahe", -21.3667, 15.4500, "Erongo"],

  // ── Hardap ──
  ["Mariental", -24.6333, 17.9667, "Hardap"], ["Rehoboth", -23.3167, 17.0833, "Hardap"],
  ["Maltahöhe", -24.8333, 16.9833, "Hardap"], ["Gibeon", -25.1167, 17.7833, "Hardap"],
  ["Kalkrand", -24.0667, 17.5333, "Hardap"], ["Aranos", -24.1333, 19.1167, "Hardap"],
  ["Stampriet", -24.3333, 18.4333, "Hardap"], ["Hoachanas", -23.9167, 18.0667, "Hardap"],
  ["Solitaire", -23.8833, 16.0000, "Hardap"], ["Schlip", -23.9833, 17.2333, "Hardap"],

  // ── ǁKaras ──
  ["Keetmanshoop", -26.5833, 18.1333, "Karas"], ["Lüderitz", -26.6481, 15.1594, "Karas"],
  ["Oranjemund", -28.5500, 16.4333, "Karas"], ["Karasburg", -28.0167, 18.7333, "Karas"],
  ["Bethanie", -26.4833, 17.1500, "Karas"], ["Aus", -26.6667, 16.2667, "Karas"],
  ["Rosh Pinah", -27.9500, 16.7667, "Karas"], ["Berseba", -25.9833, 17.7833, "Karas"],
  ["Noordoewer", -28.7500, 17.6000, "Karas"], ["Ariamsvlei", -28.1167, 19.8000, "Karas"],
  ["Grünau", -27.7333, 18.3667, "Karas"], ["Koës", -25.9833, 19.1500, "Karas"],
  ["Aroab", -26.7833, 19.6333, "Karas"],

  // ── Kavango East ──
  ["Rundu", -17.9333, 19.7667, "Kavango East"], ["Divundu", -18.1167, 21.5500, "Kavango East"],
  ["Ndiyona", -18.0333, 20.6000, "Kavango East"], ["Mukwe", -18.1000, 21.4000, "Kavango East"],
  ["Shambyu", -17.9500, 20.1667, "Kavango East"], ["Rupara", -17.9000, 19.5000, "Kavango East"],
  ["Bagani", -18.1167, 21.6167, "Kavango East"],

  // ── Kavango West ──
  ["Nkurenkuru", -17.6167, 18.6000, "Kavango West"], ["Mpungu", -17.7500, 18.0333, "Kavango West"],
  ["Kapako", -17.8500, 19.4167, "Kavango West"], ["Musese", -17.7000, 18.9000, "Kavango West"],
  ["Tondoro", -17.7333, 18.7500, "Kavango West"],

  // ── Zambezi ──
  ["Katima Mulilo", -17.5000, 24.2667, "Zambezi"], ["Bukalo", -17.6167, 24.5000, "Zambezi"],
  ["Sibbinda", -17.7833, 24.0500, "Zambezi"], ["Linyanti", -18.0500, 23.9500, "Zambezi"],
  ["Kongola", -17.7833, 23.3333, "Zambezi"], ["Ngoma", -17.9333, 24.7000, "Zambezi"],
  ["Sangwali", -18.2500, 23.6167, "Zambezi"], ["Chinchimane", -17.7500, 24.3000, "Zambezi"],
];

/* Accent- and case-insensitive prefix/substring search. Prefix hits rank first so
   typing "ond" surfaces Ondangwa before Uukwaluudhi. */
function normalizePlace(s) {
  return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[ǁǀǂǃ]/g, "");
}

function searchPlaces(query, limit = 8) {
  const q = normalizePlace(query).trim();
  if (q.length < 2) return [];
  const hits = [];
  for (const [name, lat, lon, region] of PLACES) {
    const n = normalizePlace(name);
    const i = n.indexOf(q);
    if (i === -1) continue;
    hits.push({ name, lat, lon, region, rank: i === 0 ? 0 : 1, len: name.length });
  }
  hits.sort((a, b) => a.rank - b.rank || a.len - b.len || a.name.localeCompare(b.name));
  return hits.slice(0, limit);
}
