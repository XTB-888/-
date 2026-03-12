"""RAG 寓言模板库 - 向量检索服务"""
import json
from pathlib import Path
from typing import Optional

import httpx
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.models.schemas import VisionAnalysis, StoryStyle


class DashScopeEmbedding:
    """阿里云百炼 Embedding 封装（直接 HTTP 调用，避免 LangChain 兼容问题）"""

    def __init__(self, api_key: str, base_url: str, model: str = "text-embedding-v3"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """调用 Embedding API"""
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }

        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # 按 index 排序确保顺序正确
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量 Embedding（每批最多 10 条）"""
        all_embeddings = []
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(self._call_api(batch))
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """单条查询 Embedding"""
        return self._call_api([text])[0]


class FableRAG:
    """寓言模板库 RAG 检索"""

    COLLECTION_NAME = "fable_templates"

    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embeddings = None
        self._templates_cache = []
        self._use_chroma = False

        # 尝试初始化 ChromaDB
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "寓言故事模板库"},
            )
            self._use_chroma = True
        except Exception as e:
            print(f"⚠️ ChromaDB 初始化失败: {e}，将使用本地缓存模式")

        # 尝试初始化 Embedding
        if settings.dashscope_api_key and settings.dashscope_api_key != "sk-your-dashscope-api-key-here":
            try:
                self.embeddings = DashScopeEmbedding(
                    api_key=settings.dashscope_api_key,
                    base_url=settings.dashscope_base_url,
                    model="text-embedding-v3",
                )
                # 快速验证
                test_emb = self.embeddings.embed_query("测试")
                if test_emb and len(test_emb) > 0:
                    print(f"✅ Embedding 初始化成功，维度: {len(test_emb)}")
                else:
                    raise ValueError("Embedding 返回空结果")
            except Exception as e:
                print(f"⚠️ Embedding 初始化失败: {e}，将使用关键词匹配模式")
                self.embeddings = None
        else:
            print("⚠️ 未配置 API Key，将使用关键词匹配模式")

    def load_templates(self, json_path: Optional[str] = None) -> int:
        """加载模板到内存或向量库"""
        if json_path is None:
            json_path = str(Path(__file__).parent.parent.parent / "data" / "templates" / "fable_templates.json")

        with open(json_path, "r", encoding="utf-8") as f:
            templates = json.load(f)

        self._templates_cache = templates

        # 如果有 ChromaDB 和 Embedding，加载到向量库
        if self._use_chroma and self.embeddings:
            existing = self.collection.count()
            if existing >= len(templates):
                print(f"模板库已有 {existing} 条数据，跳过加载")
                return existing

            # 清空重新加载
            if existing > 0:
                all_ids = self.collection.get()["ids"]
                if all_ids:
                    self.collection.delete(ids=all_ids)

            ids = []
            documents = []
            metadatas = []

            for t in templates:
                ids.append(t["id"])
                doc_text = (
                    f"主题：{t['theme']}。"
                    f"冲突类型：{t['conflict_type']}。"
                    f"情绪弧线：{t['emotion_arc']}。"
                    f"故事梗概：{t['synopsis']}。"
                    f"寓意：{t['moral']}。"
                    f"关键词：{'、'.join(t['keywords'])}"
                )
                documents.append(doc_text)
                metadatas.append({
                    "title": t["title"],
                    "theme": t["theme"],
                    "conflict_type": t["conflict_type"],
                    "emotion_arc": t["emotion_arc"],
                    "ending_type": t["ending_type"],
                    "style": t["style"],
                    "synopsis": t["synopsis"],
                    "moral": t["moral"],
                    "keywords": ",".join(t["keywords"]),
                })

            embeddings = self.embeddings.embed_documents(documents)
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            print(f"✅ 成功加载 {len(templates)} 条寓言模板到向量库")
        else:
            print(f"✅ 已加载 {len(templates)} 条寓言模板到内存缓存")

        return len(templates)

    def _keyword_match_score(self, template: dict, vision: VisionAnalysis, style: StoryStyle) -> float:
        """关键词匹配打分"""
        score = 0.0
        if template.get("style") == style.value:
            score += 10.0
        keywords = template.get("keywords", [])
        for trait in vision.personality_traits:
            for kw in keywords:
                if trait in kw or kw in trait:
                    score += 3.0
        if vision.item_name in template.get("synopsis", ""):
            score += 2.0
        hint_words = vision.story_character_hint
        for word in ["守护", "等待", "孤独", "勇敢", "温柔", "坚强", "智慧", "自由"]:
            if word in hint_words and (word in template.get("theme", "") or word in template.get("synopsis", "")):
                score += 2.0
        return score

    def retrieve(
        self,
        vision: VisionAnalysis,
        style: StoryStyle,
        top_k: int = 5,
    ) -> list[dict]:
        """检索相关模板"""
        if not self._templates_cache:
            self.load_templates()

        # 优先向量检索
        if self._use_chroma and self.embeddings and self.collection.count() > 0:
            try:
                return self._vector_retrieve(vision, style, top_k)
            except Exception as e:
                print(f"⚠️ 向量检索失败，回退到关键词匹配: {e}")

        return self._keyword_retrieve(vision, style, top_k)

    def _vector_retrieve(self, vision: VisionAnalysis, style: StoryStyle, top_k: int) -> list[dict]:
        """向量检索"""
        query_text = (
            f"物品：{vision.item_name}。"
            f"性格：{'、'.join(vision.personality_traits)}。"
            f"角色：{vision.story_character_hint}。"
            f"风格：{style.value}"
        )

        query_embedding = self.embeddings.embed_query(query_text)

        # 先按风格过滤
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,
            where={"style": style.value},
        )

        if not results["ids"][0]:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

        templates = []
        seen_conflicts = set()

        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i] if results.get("distances") else 0

            conflict = meta.get("conflict_type", "")
            if conflict in seen_conflicts and len(templates) >= 2:
                continue
            seen_conflicts.add(conflict)

            templates.append({
                "id": doc_id,
                "title": meta.get("title", ""),
                "theme": meta.get("theme", ""),
                "conflict_type": conflict,
                "emotion_arc": meta.get("emotion_arc", ""),
                "ending_type": meta.get("ending_type", ""),
                "synopsis": meta.get("synopsis", ""),
                "moral": meta.get("moral", ""),
                "keywords": meta.get("keywords", "").split(","),
                "distance": round(distance, 4),
            })

            if len(templates) >= top_k:
                break

        return templates

    def _keyword_retrieve(self, vision: VisionAnalysis, style: StoryStyle, top_k: int) -> list[dict]:
        """关键词匹配检索"""
        scored = []
        for t in self._templates_cache:
            score = self._keyword_match_score(t, vision, style)
            if score > 0:
                scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)

        templates = []
        seen_conflicts = set()

        for score, t in scored:
            conflict = t.get("conflict_type", "")
            if conflict in seen_conflicts and len(templates) >= 2:
                continue
            seen_conflicts.add(conflict)

            templates.append({
                "id": t["id"],
                "title": t["title"],
                "theme": t["theme"],
                "conflict_type": conflict,
                "emotion_arc": t["emotion_arc"],
                "ending_type": t["ending_type"],
                "synopsis": t["synopsis"],
                "moral": t["moral"],
                "keywords": t["keywords"],
                "distance": round(1.0 / (score + 1), 4),
            })

            if len(templates) >= top_k:
                break

        return templates


# 单例
fable_rag = FableRAG()
