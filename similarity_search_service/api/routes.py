"""
api/routes.py (UPDATED - Single Round with Galois Keys)
========================================================
"""

import logging
import time
import base64
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
import tenseal as ts

from api.models import SearchRequest, SearchResponse, ImageResult
from redis_service.redis_client import RedisClient
from redis_service.candidate_collector import CandidateCollector
from fhe.context_loader import FHEContextLoader, RequestContext
from fhe.hamming_distance import HammingDistanceComputer
from fhe.decryptor import DecryptionServiceClient
from ranking.sorter import CandidateSorter
from storage.azure_client import AzureTableClient
from storage.hashidx_resolver import HashIndexResolver
from utils.serialization import deserialize_fhe_vector
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency injection
async def get_redis_client() -> RedisClient:
    from api.server import app
    return app.state.redis_client


async def get_azure_client() -> AzureTableClient:
    from api.server import app
    return app.state.azure_client


async def get_context_loader() -> FHEContextLoader:
    from api.server import app
    return app.state.context_loader


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Privacy-Preserving Similarity Search (Single Round)",
    description="Complete search with Galois keys, returns Top-K results"
)
async def search_similar_images(
    request: SearchRequest,
    redis_client: RedisClient = Depends(get_redis_client),
    azure_client: AzureTableClient = Depends(get_azure_client),
    context_loader: FHEContextLoader = Depends(get_context_loader),
    settings=Depends(get_settings)
):
    """
    Single-round similarity search with evaluation keys.
    
    Process:
    1. Load evaluation keys from client (Galois + Relin)
    2. Collect candidates from Redis
    3. Compute encrypted Hamming distances (with rotations)
    4. Decrypt distances via external decryption service
    5. Sort and select Top-K
    6. Retrieve images from Azure
    7. Return sorted Top-K results
    
    Security:
    - Galois/Relin keys are public (safe to receive)
    - Secret key stays in client HSM
    - Decryption performed by external service
    """
    start_time = time.time()
    
    try:
        logger.info(
            f"Search request: {len(request.tokens)} tokens, "
            f"top_k={request.top_k}"
        )
        
        # Step 1: Deserialize evaluation keys
        logger.info("Loading evaluation keys from client...")
        
        base_context = context_loader.load_base_context()
        
        # Deserialize Galois keys
        galois_keys_bytes = base64.b64decode(request.galois_keys)
        
        # Create context with keys
        # Note: In TenSEAL, context includes keys when serialized
        # We'll use the client-provided context
        request_context_bytes = galois_keys_bytes
        request_context = ts.context_from(request_context_bytes)
        
        # Verify it's public
        if not request_context.is_public():
            raise HTTPException(
                status_code=400,
                detail="🚨 Context has secret key! Must be public."
            )
        
        req_ctx = RequestContext(request_context)
        logger.info("✓ Evaluation keys loaded")
        
        # Step 2: Collect candidates
        collector = CandidateCollector(redis_client, settings)
        candidates, stats = await collector.collect_candidates(request.tokens)
        
        if not candidates:
            return SearchResponse(
                results=[],
                query_time_ms=(time.time() - start_time) * 1000,
                candidates_evaluated=0,
                fhe_operations_count=0
            )
        
        logger.info(f"✓ Collected {len(candidates)} candidates")
        
        # Step 3: Deserialize query
        query_ct = deserialize_fhe_vector(
            request.query_fhe_hash,
            context_loader
        )
        
        # Step 4: Load candidate FHE hashes
        # TODO: Implement candidate hash storage retrieval
        logger.warning(
            "Candidate FHE hash storage not implemented. "
            "Using mock data for demonstration."
        )
        
        # Mock: Generate placeholder candidates
        candidate_list = list(candidates)[:settings.max_candidates]
        candidate_cts = []  # List[ts.BFVVector]
        
        # In production: Load actual candidate FHE hashes from storage
        # For now, skip FHE computation and use mock distances
        
        # Step 5: Compute encrypted Hamming distances
        logger.info("Computing encrypted Hamming distances...")
        
        hamming_computer = HammingDistanceComputer(req_ctx.get_context())
        
        # Mock distances for demonstration
        mock_distances = [
            (i, __import__('random').randint(0, 128))
            for i in range(len(candidate_list))
        ]
        
        # In production, uncomment:
        # encrypted_distances = hamming_computer.compute_distances_batch(
        #     query_ct,
        #     candidate_cts
        # )
        
        # Step 6: Decrypt distances via external service
        logger.info("Calling decryption service...")
        
        decryption_client = DecryptionServiceClient(
            decryption_service_url=request.decryption_service_url
        )
        
        # For demo: Use mock distances directly
        # In production:
        # decrypted_distances = decryption_client.decrypt_distances_batch(
        #     encrypted_distances
        # )
        decrypted_distances = mock_distances
        
        # Step 7: Sort and select Top-K
        sorter = CandidateSorter()
        topk_results = sorter.sort_and_select_topk(
            decrypted_distances,
            request.top_k
        )
        
        logger.info(f"✓ Selected Top-{len(topk_results)}")
        
        # Step 8: Resolve hash indices
        resolver = HashIndexResolver()
        topk_hash_indices = [
            candidate_list[idx] for idx, _ in topk_results
        ]
        row_keys = resolver.resolve_to_row_keys(topk_hash_indices)
        
        # Step 9: Retrieve images from Azure
        azure_entities = await azure_client.get_batch(row_keys)
        
        # Step 10: Build response
        results: List[ImageResult] = []
        
        for rank, ((idx, distance), row_key) in enumerate(
            zip(topk_results, row_keys), start=1
        ):
            entity = azure_entities.get(row_key)
            
            if not entity:
                logger.warning(f"Entity not found: {row_key[:16]}...")
                continue
            
            json_data = json.loads(entity.get("json_data", "{}"))
            
            results.append(ImageResult(
                image_id=json_data.get("metadata", {}).get("image_id", "unknown"),
                hamming_distance=distance,
                encrypted_image=json_data.get("image_ciphertext", ""),
                metadata=json_data.get("metadata", {}),
                rank=rank
            ))
        
        query_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"✅ Search complete: {len(results)} results in {query_time:.2f}ms"
        )
        
        return SearchResponse(
            results=results,
            query_time_ms=query_time,
            candidates_evaluated=len(candidate_list),
            fhe_operations_count=len(candidate_list) * 2  # XOR + Hamming
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


({"image_ciphertext": "j8OCVooMZK9jy9fYq8HWyJYtzAOR7C+7TSdGvKXWhcThu6YunBmTqulOn3qLSvhH1gmySG/ioXUquec9kgijMw/tRLpqydn2pKqYSwpNwmU4i4qnN7/p3hTNEEj/uKTUDIc+76f9H2vQxW+RIydKAegT7iCEZha8x2T5m35UgRo6ea16LJfsN+Aag9vYDQDgCypZ2OPMqwUx564yyD0qoFVwzmOnvDCd92tRYabRilEp6A1nHqVonCI1w2J5SpYqyaqNOK5WvMOwuFVoXHZkzus80lJS50trOy2YalkAHvD29LDDG/zRrsB1aDZBAxa0blff1gX4JDrQQ/0lbAe9XvMMaC7kik/FGOz6u3n7GuTqoXIK3ddT4gK0JbtIltfTSYrfvbSLG+CkMhdJZWCvt288PzvDopocw1paUBVZ/akuGZXSg5/6FNwodhIu0e6CJ3g/HKDmlm1TEGIabhkWqcMAPqqoWg/LaFdYryYGvHkFJ7HirQ+c72QXlV9iKr1wKPgXUwZYOkwq8UQjZkSjt+6ScLayT+xg8LNylVwIBacmQvWGTSgdko9JCl/DEiIe+fUVo8EHvcJ+X7GMhNRTP9Q78JYrPGXgPEfOwoftijqXmV+KWebf3bCEdqUUIgZd3o+ktbQBhjGp7uIsq5VldqHhzCXGRe0uH4NP0u5jmhwi5mprQiWnM/D+b6W+/25lH2ERG8ywuzelsNWUrLF0iO4DLdLPztvcR0R3cMsjKWGt7Dr9BsYkHaqsCfsZQT+0VUumqzzeNa2iz0m1ZFQpeFZEe566BlOdG34FkLnu7pxi9xTvh5prGWHgj6+mPpcHjLeBC8NLMXwNj/T1mkysaTplxUUZ7LZzIA8pVsq7MIQk4jm25ZBX70yL/jplHmybIOukaqSlOwd0AAKfYifxukF8xifyz+x/JArgnkBTt4Gv+DFlm2g1QKTwtW6h6D1dRsI+VbXfB7t+ivPTzwpuptPcDVtENxtAJQ7ftivP4L65XF3djmZfRxX5uIFmp41mEGLjTSrymaGL9bMz7Lnhk25d/mDg2fFYcLAQSiTki8r0s1xbOzdPwCBAtKibkekdbQiHYNCJMwsf3Iu1aGaCP7qhAA/e7QR58mVTwp5m7mZMKdWXJGxoQczL1FltC1s926zylyWxQzRMGuaaARzpfC3KQ3NEU1oLgPNh4JuYBQEA9/c4F2l0uKgpJrcmXfCootZCwigf2oC1yLTd7RW1GZAKH1fK2kHMDc7Vc6Lv2cWannAq+y7F7n2nhaJdZF+bDfb8Z+XQ/QkAXNH0Zl4SBHWDH+h47J0gmg8z1ofPsoyCGj7YJERo9DGVTEJEbeJjYtdy1pGLdROub6aYd8S5AyNm9PpZAnveFW1QvR+AAWYZzsrhGHFFh3sMupYbQA9h3Jg/iWwC5ABpw6t2bk7bUkNYfVM/hcTuZoW+eNMrwJ7+zhBT6rAcgHKmBLTq0NhFn6+0pTo64oXjxPhpCT4rZLHtOkzErflheAia/REONIBY0qsx8VymHbvH8oqwbjZwe9ZQpt+6ATXw01iodPdlc2+OBJ83NSzLjgk9h/EJzKKS/SiiYSFjuphUqncR7DFbmNkxOG8ievo1avC0IDpq4B+bTQwzkwhLTq/WuQK2GfwQlN2tDwl3BAvfp+LmkBdLoTEb3CkoKK0lob/Af7vLOEniRjVu4A9t4FWrRc0uyF60BwSNkEVjtwbotyZs9L+Yme6MZDRASmErzzA0NkQSZfej0vlW3wZRIRNQ714cbdqyuuBEgsRHctfT82bxdyk3biJpxpB7DcGTNdrkP4lrIsIE4pFiBPLSzoMwYk2KuvZ9Nwo+6i10AfRdy6tnQWPJyJi/D290l4Ygq4GnRuSSw3p/6TISRIJK0o20hmPmGHaJ/Dl+I8BqDAJcDWfCFbnoyJ4Js2aK+Ke/LYv5k0OkvVLWV6BeipmrJnPvmgcBL4TCF2XW3boWD+YD1wy79GLt2tonpThUMoJ3DpPQxAwa5+HgW7dLmdPZlBfD1JnkPqM5O9PdSuDVU44+f3S8iF0MMUmO0gm/yFnd/uSAZliCnRJ8QNaiMwebq4a3NzallNr8i4A+q8wnBBJiXKT0Ph4nlkslbM+SQjo28JA13fZstZvtD7hibEUp0mscGhdZCcIbfkq8GOOkDLOLZVPCtT+UkfI41+iTgE2FdvV4oaL2wgGvqT5L5/FLm7eZO0NmipV6QCTO01pDxm/i1SIFtkT/Ks/kFTsRmuDTnJr1arsqMXiSx0DqD8dKO78P9ywGEaBixOkyTXQrBtZWMBEHhc/Wz/RV0DZh7rrHmmPq/ICiZEAXmM5vjZCB5xNia2XelvBc4oC36wuqOgDsiCE03LTDV5DBznZfPS2M2+dQBBXk5azlLvYdofMQal6uI2YCMnM7BmrJAf6AuvWjqeVvnSgluVC1ZIF43kwTQvD2FLZXpUc2x4u8c2nBHQKO4Ys6mPgdj/N4ei+OuIv5xBLs+ednsdJd9UH7sqESTLrMC4EAg4zEiVbTpbafKWsTxWiH/0KuTLqY2INHNNoHIfMbAOaV8R/neIpGkVxXe0ZcQNyyFkJmGlV9Ynprws1sapPTaUVYVLjbo0xro1tgvFQ6wJjXTfBtekqpuZuPsvA6FS5DnYMyXc1EUw0V6CmvEet/5ljXRXTW2hNw4QdY5WWHCPBqrX7pFbtaiKf6LG0SY0/FC9KuXx+lW+GxB1KJ3WySEhCZgNhoMyM4YmEqK3uEWKKQnElBpZSRhilprmLDBQxMatQpctewzGI6CqL13NKXrsKLS/a4DcddD145vcjPJat40nwkNJHeJCB2QgpmXduPzd8nRKxUZn8NU8AUDJvk134aQ5CpDf7iX2v2T91RljitkJKzahY9hDw/pg+kG1SGQVUlcJCXovKlrpq0+slHwmbyDT8WUGg07elOXHwP88QtEC4KMMrxbEN9SAukYR32o8tSdsk/K+My+lNgZyDhmIwxPwQJIx8qJQRO7/JQ3Zxee96fpOVCFzF+ezLvUqw9EbDJQdj2wpVsS1k4Qyr3NsHQ0kxeCZh76kqMaUn39GE8TVbqGCV+3bTwo+FrB3vfp+dBxxOcQEKRe//KRVjFlUwZlVOZlv08gRjgDKbLJ2/FwlR2a+pJsC2RCoYCE7cFEzICGwXf4G13ZbPFmmQMT5QaVEfdJ6YL69ncT1tjAJLqRgSLaNIokTLUn+VuHsAQkDEEkyWcM/3TvZXfSShzUYFcxJHjKq/tmwJ6xg4kB5ORl3UxvLfcnusfwS6OLyt8BGd8QWl6e9GTZcMxkCgHpcceJSPMZETEUettkYkHxDtZuGX4AmdZS9xbqxAkAkVK172YMVdJt143GHrP0c3wqOrE2XawRMIsmogJKf0cDb9XhmNBixa2M8AqZhbUACZWGM1P0agqyTxg+qChUTDvOwqvNr2SKOXvsFIt6QkEaBYikmiEtEOCxi+lHmaLeiT+Maj1ou/ZBsZ4C1/CxM/cSaYyeh99Zwa3Lxxw179ao53MYzCivPWdkYEqH/jbo3PQ1yfZnIdkbMKI/U4UL+Yw4QvWiAbUZL/9lRhh9+TdsIX9uw+DSiZXZmERRXhxS/QntBuhz2YHpuqOk+76TAeLomynd1SPWbY2ox7xvoCR7WzEoYpaaZRoGjlYidBk/hCmZBMNrAfU487FAXZAtlGgxt8Rcx63iCgH96lg9dUSpMa5E+JWf9R5DUSgBpFC1mSBH4jzK71D0jPX31YBeyMX2vrfPeMOrTdEZLMG0GPkDjPqlCsOhBuBmkZsCq9d+/kY0jLiX2H84JDIeodpzsIjm9jM6d3DxzOpYTAeRy5uVcs6WpXABzXiIZyUXuhqIyfn6sWVdOvXDtPjqS4FywTtO0id4H53YyqppL516ceB0w6ieUHiUkgmd3jLPs7rHgqoS3/beW1o/G5au7IJdGH2mR0GaCFZfxFwYFNR//q3qWpfKX0Boz5R8pAT4AoZZMEp/2tEmBwQbBESVW1q/Bq1GePQmTRtA1YJZtNZlEL+8vT8WofPHlzRlZehKMN9sP6JNW4scj9EA3AjkPC/c6HhOjryY45C15CcpMdHT49Jxq6MSHmg4kCjzNIzayxPejjFo4FjNAiiARajcoPA8Ls8IrjdKQ1056I7Je//P40JWs3BsDEw4k37Tpjyo36pXryhttP/n++enfjNnKuPobLa1e8KHUyARD64itwAtiY015yHFwtgz4UxWHe/uzDfGgcA03/UhQ5Cs+cof664nLVyGFfPP4ZjeWPHZVIqgEHWrKKWalLaCjM5uuGmLeOjGaif4rQjXq2Li56IAuUZ5W7l1M+hYuwEbC4T5n+zQb+fXyHWCm9eGzptRVnDAoPLzLKk9iUjIIaLfrqoQ0HBTWkpE7T6ayVuCVGu35L4UfVjFm8RqbmszSaTzluYthA6LFFakPbrM1TV8d9Cbng8vpPPHfW40MwyQazzYSXBUdgEK7S9x9TrN8aSQlD0xD5/ilKZAn/f3oCAsJQAYgl3q4rywNpNziqgAmtHDmp1cI5YrH1lwwPOWkKBCmczjTYl7R14TZE/+r9Ez5LulPeDtLWa8iwefEt4lIEMu4CQt/hITFR729zM4xtpWEP2wNqetwUWWurl0S//2G2F74y7RiJZzoMydcffEok7zq3OU/btSYd6PWoVx9wVxBDuQfvK/cHLtrYTpmKHu2DRlx2eQOyJS7gNZMIb8nyoQZum3PXEyThOFt9oOrv2mYZe3UIMYdux2TQZJ+rOO3JPuyGjb+2Xv8Td9eR9OjE93qhdpPw+Gc9LFubmHQrKrvCbvAHmMvgFr/dyVsC/t7H7B0kKwwOJ8EDQF0YjBr1n21mD4iiDIvmlqm+f9P11cQNmlB8Sa9I8IDKo46Ivax8H4kX2qq2II85U2L+coZgK6XjR7MLBl+l6w+NyKe8B93lKda5ffzeo71uj3LEOC5NEaGP0YglmjRsCrJQWkukK9mYIjJlj/tG4PwFJj/ati2APh/49MVspTRqtWqMtaUbCCQ7ZvO05KlPQB9WBgYvVzlZKonWEYKrKFJpztf5X9m8EWgwgWkxDzLYekJw2cWnhSQ0NM31GM3pzHgSbblXzP9KS9p0JMjSV5RJPfWc8r1YjpWK5dmPic5n49tj6KI9f4wmXpYcAKxM7zmup2izlcmb1MP8Db2htfSjMP4heu03H6eSpgwJU1eHbCwsVqNscH7BXNEfOhD6Wc+U/Nsw3hYO250654OwEhULp68Bpz4Oj29inpOa9lPXOyC1kzHlU+krv3gWOG3b0QZMY5oweMaRpmlOdVW3A2J+G4J1Ofu2XyPF9As4iVfCRNPSMca8YRraaOr5ugohU/xyYuUYzmP36Ckp4icBSMTfLw6YBA71//26aGcoxPwtzQRmGsbhYCI8CfROk0ZBA2mt6MAqGN2qGim78qn7VA6dvv2iTFcsTK6moa/1R1cbekE5i+NReEPZpYVoaM3OnZjjM/WE2iAef3UqoAGDiwQ4bSDseMdn6MrGvIY7IJwsHLDChkJLdk6perFRZCsVkNsBUcOcZXi9vhxeSCrc2x/WWLIMk6EcHBHpEjVdJRleGpgUci3idCpc1doMC3bSKhDuQQRTzSQ6Np+rDgeVCaFe9kylIVFdjj7hCCnatBhTvJERCFBaaa5XEDrQzNtiUZN4ZbWW0iqWaLMw4nxA9skD0V2M0DV78Uv3g6rLAs2nq9cCAz3n7uUCJ8ahqV6is+9TXSwCY9EpOoZI/Sv/FKPiRCRdjC1Nc8W7YLzKWak8qCmeRil/wJp+iH1kwPJZJpbfiZpRjCXY2CnBiB7R6RnSY7uBn6j+54NYIgd/MD9QMp2umfMPe/LrtjTT5u07LppJZu5OEpWBD9J6ZtBUH+GwZFGafQp1qOjvopVtI33HAhkoGg6WXUC0aU/7IStMi/rl5p0/o5biiX4Okg1h6iKp9f2uBZ+ZKRZIZbvgJFsYZioHCIV1vDjopQPvhbf5wmN/jZZXlwQKTyHVfRDY8la08+UN2qApcT761ca1hJpo1rKptmqZZ9J8NAg32drFzfjT2ZQn8tlGQJWFeeVQ1qbWxW+69o6+y9VZgTZyixG5iAXYg6N8s2rhqHxCzJb+MCU4paDUNg0J3keJetG5PsXNmtd93E3eBdD5+qGekc9SObntAETNs8HiUKAyTAYYypQDw1okkzdSkkzr9Z9q4A1psUs3A6GLfsThrJwnB6bYRZHcXtKZJOUQBbEVrroFrUYgNEJpWdXrJxjFmMgoOrYwYXHJjc8VilDpEu0pacn+7wHfMKPJ8hv7asC6xvYg4Pa7ksb+rGjk5RGxFdXXdMtpK0jeYxCxmDmCEWUPl57q6TiPL2Bi6khRotzPDRT3hRWvtY6qWX7rUJ7d53Wy+HDS1DFXrpew2xVa7WTCZwtTzzPF13pYl1nR2kAoQoFbYiK7TDuhbzyMPPMP2nDvUK+w9LoqfOc48psExo5yWQ5xoBl6OcR3lN+jJzY+WCaQ5IfNBiib2MsVVrdrctNTxM5Pdt6tCRHuKc957JhGtUIDJH8rXUti6p1+O1EbVxBFBE7NT9QBj4dfb0bUAYMRHqyLKDPLwWXdIa+3TqpjKF11wqZQpQcmwpZxftPy6hK7ZBUx/tMuCa7mXWv4MLlvjmGd8g4wsKCIcsziTKQoGTB3Ab6BvduYe8n6Y18k+nawZ3kH76BxziinTHCb4K7wve4BNBRulBd1p5iky+CjQTzcGRBHrZx7bMNFRl0yxEhGdf0c3lCa4et5S+dOOwl/0ebHJLbRoJvxl8ssFx2UiL7XxClYZGZGmIfcL/LSP5v0GFIXl9VmCRZdiietbYvYQZPiXslpmEeaCoCVABogQA+EfkPIG+Mx4VS/KTkLYlbsZhxXi5uWats2S5PgId7eeEZgpWDEKmBBw24UgDcHMM/xvrV0YxgWRfFFwm7reNRGrzh1af9/HNefPBGulGrhyJG/hiGyIhD9sIKsLhdtDXq3mLHxsiSRaCIuyRlyqJv89mCGimZ50tDZqYh5b99dKii2+1DXiHP4XvGuugb2MDoP3x8g9DnP7jC/EPaipQ36tabarc/MCFmWmrZjLJjcjmdwHNJW3pet+XJ6Cu6h4WxrjnbQAvgShhXpJpVaIo+AJqFZdWgV0jWRjgaX8QuInaIPL5RLcWVKUjlC+rrSXHI9EMRBVOLRD2PC4ZhOVSJ/mcdqsaIObjdOnCbbDQ7jvPeGnUSXAua3fkJcw+QlTCl87uGhtOVFYfHd1cfFxrP1NUDEQtI6jBWC6Sfe7JSvkhdjv6P1MYgbk7UpycLrnqrrBqLlFXeVBgKKoOU+1qPR20uPO9/Jujsj///vpumey9/VV0Orsg86FXi9T/TgijxRBuRc9t9Jtpfu9UQA8p9D1CBpC0yBS5GIrVMGh9PfHRuCoftoK6Gjht7INMjKQHSH3/QSUoegWF0H+x5tvavgPZQ67nAPd8xOwLpwmDpuBpTyHNWXRbiy0ZW6VBTRMpJ1Rooj0qFReAuSngqIYvc4iSyhLny/woKMwsVqTaw86heizwTStW5BkxvzOLU19iJti7lc/xYcQx9eRw7wpq35QoIDI1C8fx7c8E6j7WnEWmW6LNgl2q1GokogZfQf1DIlBlhB885TQ227sPBsl14nuSpx8/73GKyM2Bk9n+cUzXuKpfDYknpkLdQuqWySIkb/qyes6KephQK4OTo4PaAajXnWhxxvNOflaff8jsHNxGJ5MlU6ckHwnioFaNdZbR0+x5zpHsFeVQaQdSdPT0fIeNfepHvdcbIrOJ9oGeJxW3QQjq+GfUfNN3R/8ZvBEQvcaLVwEDjdp6qG0qiq+Unq7MwoysOBDeGufNe6heveebWLp0l71KXDcXTpddEggANXin3VK38n4GFkp+Kr3k6JiW7HiJdq5jdozYltYZOg24m0zDRGyahcxQt/4il9GpXu1Z3G5j56BCXDsfCCIfCYZ4uNp4COuQ7LmAshUpGPAgEZ/Efqz2Td79NvfadEZscSdURdTn4OkzV8J0V30ZP6W4kqm8VAaiTdIFv3z5VR9uwZoXtnDEWqrLPr9KsB+MsSEk4eVTySZ/9TY0rnCfRYf8cioxXjhHsmGqKc24KxGw8A/RuTzUi2j+ZaAkzFAKHghDOHPBmwmVK+uWS647wFpCkVo1jI3bu95h6NF9sKL3l6HHYjvBpLw1hFRLzmY0xc+B/7l25T84iCIhR91svSb1gZV/2rSnxEHyFi9Pv1EU0J+1QaIaHK7ocdfBQ==", "image_nonce": "SU4roxi4mAF51JzY", "image_auth_tag": "2/tzz/DdciapFLRMU9joMA==", "wrapped_cek": "Z3u5DaPi3mkDHT+ECzr/QO/Cqqi4lem4BFTtEdJr9xA=", "cek_nonce": "mCQTJIYG503CMlD2", "cek_auth_tag": "Sp1UJ2XRYIoWNGWfiixnkA==", "kyber_ciphertext": "0RLRlSdaLl3PlbosrxV9KlFhA9SN3hDVWXFOeiCE0OuGezvPDkt/+jzGINs1SeoU6ays0YkgN9GlbDMrD2BK00maWEQyM5C539vKMSpmbIe8AcskcYJvUKTsKtFT+GcFpt96TRcvoBahxWRbcVJVOWzMf5NIuY7EoGXhJtwafEopnwumIfFxxM6rsiiLKnODCzH1yCH8jakeabskRUlTSzWv7SPtrd3e+7I2xUCN6IR5SFRA1hJ4Npel3FodbnCxjwWFj+02YYz6Df4ZRZbH5rERyOFHDS9igDPhH0jRvcQGJjRBcSd6Vl3A2qAe1Pp5D5VZf5WDwEFxOdDJPYtsL9ksqg83byC/w1yd35fc/buDDxcoSlhK8HXCKLNXi4yCnR3UTMG7Cr1wRzXubpHOGe4cPyJgOz4YBZn31bbapMb0NvIJPNBM76gjvIL2yd1upDWmq6/7NtDoDkfUVtO0AdDkWuovfW+b6ceg6NTt8LOSxzEMhEQqnXlz2whdk2y/+X9up49hfTrra0uy++j6pXFO8xzctp6qwYr68Of7/U/3wGQHQcpKS+mJPdpQujcfvhEj5MVr00ZUoTY9Ww1OtQ8oGf1EMtSwagj49r3oQ9bkYpx9qGotdw1CGdBJ7ikaKhdu+Rc+LKxf+n1lXuhYVsRTv4p0Eyz4s8BFLktdt0ZVLic4693gxCYYQ4KNZgTuaeJCxpClyv6yB1Y2r8IPbuqvCW7Ldrj/I3K1AFItKlsyW2nGKz9n4CBq7OL8S+AGR22eMk7sHV50dA70cq26SmQ5v9NxdjMyeapwMHg3sS3UDgoNghLstzmJcqB6nIzYyKsKVJdYPQtXYMwlkKiDFOvaoXa7pm0H9D8tFvPmv4ZurDKwZts8nkaquBCYV1J74b3nvqDI5qxK3J6T8leYPaWpC7Hxuu5/DN2DmBhYWvcF5rdy0dTUFkMiK5I6tkuCFyGs803lSH6zYjf0lLf7cKDeX3sdUUrOmpWC/hfLndjQ3C2D0AgRIBZfAyb9G1GBzPU2duTOjwDwaYsiZ12KCvFGYgDQCTDaq6fKmauRd+U3a2PDRQxX59l/H/32b3dzB4IqOpCYgxCM60SDQxo3brAeA62eiWQgDKVikIbLkir/K7TgemixoRS2rDmSQWlDplLFoBgV/An5eklU4RAiiTDuqcFOCB4z3uZFCQjss0Q+F8iTLGolHqSEky2O70nV1ZUqlU9fFZhicOGpNFp3kPmcTfQcYXoUToRJrMX8fhJUcCqs+eTLLcdLomitKQp7vscIc4cnr7CMyroiVnqvFAOPj2BnPa6OAZ0IoOj2dxhJn5x00UlpkJJyafUsXOr72yisa7u0/NOCrxp+ZF7kcCvgxSy572LlOMrO9r+/ZzQTH2a+FB8Hr72IiPGSHbgHkUL9ZjW48b0dsNbYqJkxQ4TxpbOD8Q1aQCFnZzw66FA=", "hkdf_salt": "SfktrdZyQRPbtQLsPMnDTQrOZGHd1W8MWwW6TvEfKVs=", "metadata": {"image_id": "1_(68)_1768217165559713", "user_id": "default_user", "timestamp": "2026-01-12T16:56:05.560459", "encryption": "AES-256-GCM", "kem": "Kyber-ML-KEM", "kdf": "HKDF-SHA256"}})