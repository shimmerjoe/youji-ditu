import assert from "node:assert/strict";
import test from "node:test";
import {
  destinationItemsForGroup,
  normalizeRecentSearches,
  normalizeRecentVisits,
  rankSearchItems,
  rememberSearchQuery,
  resolveSiteHref,
  type TravelSearchItem,
} from "../src/site-search.ts";


const ITEMS: TravelSearchItem[] = [
  {
    key: "qingdao",
    title: "山东青岛旅游攻略",
    subtitle: "海滨、啤酒与城市漫步",
    province: "山东",
    city: "青岛",
    path: "cities/qingdao.html",
    highlights: ["栈桥", "崂山"],
    foods: ["鲅鱼水饺"],
    keywords: "海边 博物馆",
  },
  {
    key: "jinan",
    title: "山东济南旅游攻略",
    subtitle: "泉水与老城",
    province: "山东",
    city: "济南",
    path: "cities/jinan.html",
    highlights: ["趵突泉"],
    foods: ["把子肉"],
    keywords: "泉城 博物馆",
  },
];


test("search requires every query token and ranks exact city matches first", () => {
  assert.deepEqual(
    rankSearchItems(ITEMS, "青岛 海边").map(({ item }) => item.key),
    ["qingdao"],
  );
  assert.deepEqual(
    rankSearchItems(ITEMS, "山东 博物馆").map(({ item }) => item.key),
    ["qingdao", "jinan"],
  );
  assert.deepEqual(
    rankSearchItems(ITEMS, "qingdao").map(({ item }) => item.key),
    ["qingdao"],
  );
});


test("site-relative search links work from root and nested city pages", () => {
  assert.equal(resolveSiteHref("cities/qingdao.html", "."), "./cities/qingdao.html");
  assert.equal(resolveSiteHref("cities/qingdao.html", ".."), "../cities/qingdao.html");
  assert.equal(resolveSiteHref("https://example.com", ".."), "https://example.com");
});


test("recent searches are trimmed, de-duplicated, validated, and bounded", () => {
  const existing = [
    { query: "青岛", searchedAt: "2026-08-24T08:00:00.000Z" },
    { query: "  海边  ", searchedAt: "2026-08-24T07:00:00.000Z" },
    { query: "青岛", searchedAt: "2026-08-24T06:00:00.000Z" },
    { query: "", searchedAt: "2026-08-24T05:00:00.000Z" },
    { query: 42, searchedAt: "invalid" },
  ];

  assert.deepEqual(normalizeRecentSearches(existing), ["青岛", "海边"]);
  assert.deepEqual(
    rememberSearchQuery(existing, "  青岛  ").slice(0, 2),
    ["青岛", "海边"],
  );
});


test("recent city visits reject malformed entries and keep stable root paths", () => {
  assert.deepEqual(normalizeRecentVisits([
    { key: "qingdao", name: "山东青岛旅游攻略", href: "cities/qingdao.html", sub: "海滨" },
    { key: "qingdao", name: "重复青岛", href: "cities/qingdao.html" },
    { key: "", name: "无效", href: "#" },
  ]), [
    { key: "qingdao", name: "山东青岛旅游攻略", href: "cities/qingdao.html" },
  ]);
});


test("destination groups put municipalities together and filter provinces", () => {
  const destinations: TravelSearchItem[] = [
    ...ITEMS,
    { key: "beijing", title: "北京旅游攻略", province: "直辖市", city: "北京", path: "cities/beijing.html" },
    { key: "shanghai", title: "上海旅游攻略", province: "直辖市", city: "上海", path: "cities/shanghai.html" },
    { key: "macao", title: "澳门旅游攻略", province: "澳门", city: "澳门", path: "cities/macao.html" },
  ];

  assert.deepEqual(
    destinationItemsForGroup(destinations, "直辖市").map((item) => item.key),
    ["beijing", "shanghai"],
  );
  assert.deepEqual(
    destinationItemsForGroup(destinations, "山东").map((item) => item.key),
    ["jinan", "qingdao"],
  );
  assert.deepEqual(
    destinationItemsForGroup(destinations, "港澳").map((item) => item.key),
    ["macao"],
  );
});
