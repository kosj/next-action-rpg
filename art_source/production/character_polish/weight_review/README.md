# 작은 흉갑 영역의 제약 최적화: 불채택

두 캐릭터의 원본 runtime GLB를 유지했다. **수선 채택은 rejected, 최종 아트 품질은 pending**이다. 이 기록은 이전의 전역/높이 기반 보정을 반복하지 않고, 명시적으로 고정한 작은 영역에서 검증한 별도 실험이다.

| 대상 | 가변 welded group / exported vertex | 원래 목표 edge 길이 | normalized solve의 감소 | 같은 시점 새 최대 늘어짐 |
|---|---:|---:|---:|---:|
| Lyra, heavy 0.63s | 9 / 16 | 27.414mm | 0.365232mm | 0.250005164mm |
| Sentinel, enemy_attack 0.68s | 7 / 12 | 44.226mm | 0.515069mm | 0.199994911mm |

이 정도의 변화는 원래 보이던 갑옷의 찢기는 변형을 해결하지 못한다. 수치상의 통과도 최종 시각 검수를 대신하지 않는다. **마지막 normalized 제안은 메모리에서만 평가했고 GLB·PNG를 추가 생성하지 않았다. 최종 시각 검수는 수행하지 않았다.** 원본 손·타바드·사지·충돌·게임 값도 변경하지 않았다.

## 무엇을 고정했는가

원래 최악 edge의 정확한 rest 좌표를 수동 anchor로 사용했다. 표면 graph의 반경 30mm 안만 가변이고 바깥 ring은 원본이다. 가중치 변화 bound는 거리 envelope로 경계에서 사라지고, 변화 자체에 graph regularization을 적용했다. 이는 연속 표면의 C1 미분을 입증한 것은 아니다. 원래 네 joint 슬롯을 유지해 다섯 번째 influence를 추가하거나 잘라내지 않았다.

모든 exported key와 인접 midpoint, 즉 Lyra 2,358개·Sentinel 1,608개 시점에서 변한 정점에 연결된 모든 edge/triangle을 비교했다. 나머지 정점의 weights·joint bytes와 geometry·UV·rest·모든 모션은 그대로이므로 그 밖의 edge는 원본과 같다. 전체 mesh의 원본 최대 분포는 동일 SHA·schedule·edge ID를 검증한 baseline과 결합했다.

- 새 edge 길이 증가 상한: 같은 시점 원본 대비 **0.25mm**. 상한을 완화하지 않았다.
- edge 압축 하한: `0.95 × min(원본 posed 길이, REST 길이)`.
- triangle guard: 원본 posed normal에 투영한 후보 double area가 `0.95 × min(원본 posed double area, REST double area)` 이상.
- 가중치 비음수·합 유지, 고정 boundary와 원본 joint 슬롯 보존.

Lyra의 실제 float32 결과는 상한을 약 **0.000005164mm** 초과한다. 이를 반올림해 엄밀한 상한 통과로 기록하지 않았으며 수치 허용오차를 포함한 approximate feasibility로 구분한다. Sentinel은 새 반전이 없지만 이미 압축된 triangle의 최소 면적이 **3.770→3.620mm²**, REST 대비 **7.296→7.005%**로 더 줄었다. 이 압축도 숨기거나 개선으로 표현하지 않았다.

## solver 실패와 기하학적 한계를 구분한다

첫 raw-unit SLSQP는 Lyra에서 사실상 0 이동을 성공으로 판정했고 Sentinel에서는 line-search 오류를 냈다. 목표 edge 목적함수의 analytic gradient를 독립 central difference와 대조한 최대 차이는 Lyra 약 `4.71e-8`, Sentinel 약 `1.60e-7`이었다. 이 검사는 해당 목표·시점의 목적함수 미분을 확인하며 모든 nonlinear constraint Jacobian이나 전역 최적성을 증명하지 않는다.

같은 영역·support·물리 bound·손상 상한을 유지하고 변수·목적·제약의 단위만 정규화하자 두 solver가 정상 종료했다. 따라서 **초기 SLSQP 실패로 기하학적 불가능성을 주장하지 않는다.** 마지막 결과는 이 특정 영역과 원래 joint support 안에서 효과가 작았다는 근거다. 다른 작가 검수 영역, 의상/금속 plate 소유권, topology로도 수선이 불가능하다는 뜻이 아니다.

내부 `candidate_numeric_gate`는 실험 수치 분류일 뿐이다. Sentinel의 `pass`도 여기서는 **불채택**이다. 초기에 만든 raw-unit probe GLB 두 개와 모든 큰 배열은 ignored build 폴더에만 남겼으며 runtime에 반영하지 않았다.

## 재현

검증 당시 Python NumPy 2.3.5, SciPy 1.17.0을 사용했다. 새 baseline부터 재현할 수 있으며 아래 두 solve는 모두 GLB를 쓰지 않는다. 예제의 캐릭터를 `sentinel`로 바꾸어 반복한다.

```bash
character=lyra
source_glb="art_source/production/candidates/${character}-gameplay-001/source.glb"
review_dir="build/art-candidates/character-polish/weights/reproduce-${character}"
python tools/repair_character_weights.py --input "$source_glb" --output "$review_dir/baseline" --report-name audit
python tools/repaint_character_regions.py --character "$character" --input "$source_glb" --output "$review_dir/solve" --baseline "$review_dir/baseline/audit.json" --solve-only --solver-units raw
python tools/repaint_character_regions.py --character "$character" --input "$source_glb" --output "$review_dir/solve" --baseline "$review_dir/baseline/audit.json" --solve-only --solver-units normalized
```

최종 도구의 `--solver-units`는 물리 조건을 바꾸지 않고 numerical units만 선택한다. 최종 source SHA와 solve 당시 SHA를 JSON에서 구분했다. solve 후 추가한 CLI 선택·경계 설명 정정·SciPy lazy import는 normalized 해석 알고리즘을 바꾸지 않았다. BLAS/OMP thread 수는 도구에서 1로 제한한다.

`lyra-review.json`, `sentinel-review.json`에는 원래 불량 정점·named weights·제안 delta, 모든 시점의 최대/새 악화·triangle 진단, solver 이력·byte 변경 범위를 담았다. `validation.json`은 최종 도구 SHA·미분 검사 범위·원본 runtime 불변을 기록한다. GLB·NPZ·전체 frame 배열·렌더는 이 폴더에 포함하지 않았다.
