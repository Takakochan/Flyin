# Drone Pathfinding — テスタースイート

評価シート（subject.pdf）の各チェック項目に 1 対 1 で対応する手作りマップ集です。
`maps.tar.gz` の公式ベンチマークとは別に、**各機能を 1 つずつ確実に見せる**ための最小マップを揃えています。

> ⚠️ 書式は実マップ（The Impossible Dream）から読み取ったものです。
> `zone=blocked` の有無など一部は subject.pdf で最終確認してください（下記「要確認」参照）。

## 書式メモ（実マップ準拠）

```
nb_drones: <数>

start_hub: <名前> <X> <Y> [<メタ>]
hub:       <名前> <X> <Y> [<メタ>]
end_hub:   <名前> <X> <Y> [<メタ>]

connection: <zone1>-<zone2> [max_link_capacity=<数>]

# '#' で始まる行はコメント
```

- メタは角括弧内にスペース区切り: `[zone=restricted color=brown max_drones=2]`
- 省略時デフォルト: `zone=normal` / `max_drones=1` / `max_link_capacity=1`
- 移動コスト: normal=1ターン / restricted=2ターン / priority=1ターン(優先) / blocked=不可

## 使い方

```bash
# 全マップを一括実行（プログラムの起動コマンドを渡す）
python3 run_all.py "./main.py"
# または
python3 run_all.py "python3 main.py"
```

正常系マップは「終了コード・出力行数(ターン数の目安)・実行時間」を、
異常系マップは「ちゃんと弾けたか」を表示します。

## マップ一覧と対応する評価項目

| ファイル | 対応項目 | 期待される挙動 |
|---|---|---|
| `00_format/all_features.txt` | Parser / Input files | 全書式要素を含む。正常にパースできる |
| `01_parser_errors/err_no_drones.txt` | Parser / Error handling | nb_drones欠落でエラー |
| `01_parser_errors/err_bad_zone_type.txt` | 〃 | 不正なゾーンタイプを拒否 |
| `01_parser_errors/err_no_end_hub.txt` | 〃 | end_hub欠落でエラー |
| `01_parser_errors/err_bad_capacity.txt` | 〃 | max_drones=0 を拒否 |
| `01_parser_errors/err_duplicate.txt` | 〃 | ゾーン名重複を拒否 |
| `02_mechanics/zone_capacity.txt` | Zone occupancy rules | cap1のMで2機が直列化（~3ターン） |
| `02_mechanics/move_cost_restricted.txt` | Movement costs | restricted経由は2ターン消費 |
| `02_mechanics/move_cost_priority.txt` | 〃 | 同距離ならpriorityを優先 |
| `02_mechanics/move_cost_blocked.txt` | 〃 | blockedは通れず迂回（※要確認） |
| `02_mechanics/link_capacity_low.txt` | Connection capacity | link cap1で直列化（~3ターン） |
| `02_mechanics/link_capacity_high.txt` | 〃 | link cap2なら同時通過（~2ターン） |
| `03_pathfinding/linear.txt` | Valid path | 1機・直線（3ターン） |
| `03_pathfinding/multi_path.txt` | 〃 | 複数経路を分散利用（~3ターン） |
| `03_pathfinding/bottleneck.txt` | Conflict resolution | 4機がcap1を通過（~5ターン） |
| `03_pathfinding/zone_types_mixed.txt` | 〃 | normal/restricted/priorityの選択 |
| `04_edge_cases/single_drone_trivial.txt` | Edge cases | 最小マップ（1ターン） |
| `04_edge_cases/disconnected.txt` | Edge cases / Error handling | 非連結を落ちずに処理 |
| `04_edge_cases/invalid_connection.txt` | Error handling | 存在しないゾーン参照を拒否 |
| `04_edge_cases/extreme_capacity.txt` | Edge cases | 極端に大きい容量（2ターン） |
| `05_live_coding/capacity_info_demo.txt` | Quick Live Coding | `--capacity-info` のデモ用（容量が競合する） |

## ベンチマーク準備（別途）

`maps.tar.gz` の公式マップ（Linear path, Simple fork, Dead end trap, Circular loop,
Maze nightmare, Capacity hell, Ultimate challenge, Impossible Dream …）は、
**平均ターン数と実行時間を手元の表にしておく**のが準備です。Easy<10 / Medium 10-30 / Hard<60
の基準と即照合できます。

## 要確認（subject.pdf 優先）

1. **`zone=blocked` の正式キーワード** — 実マップには blocked ゾーンが無く、`color=black` の
   dead-end は単なる行き止まり（出口コネクション無し）でした。blocked が `zone=blocked` か、
   別表記かを確認してください。
2. **restricted の「2ターン」の出力上の表れ方** — ゾーンに2ターン留まるのか、
   入る/出るのコストなのか。実装と出力仕様を合わせて確認。
3. **`--capacity-info` の出力フォーマット** — 評価シートの例
   「Zone X: Y/Z drones, Connection A-B: Y/Z capacity used」に寄せると安全。
4. 上表の「期待ターン数」は手計算の目安です。最適化方針により前後します。
