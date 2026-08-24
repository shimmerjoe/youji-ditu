import assert from "node:assert/strict";
import test from "node:test";
import {
  rankSearchItems,
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
