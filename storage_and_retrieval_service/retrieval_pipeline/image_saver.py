"""
Image Saver
===========
Saves decrypted images to filesystem using image_id from JSON metadata.
Now includes automatic collage generation!
"""

from typing import List, Tuple, Dict, Optional
from pathlib import Path
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io


class ImageSaver:
    """Save decrypted images to filesystem with collage generation."""
    
    def __init__(self, output_dir: str = "retrieved_images"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[ImageSaver] Output directory: {self.output_dir.absolute()}")
    
    def save_images(
        self,
        decrypted_images: List[Tuple[bytes, Dict]],
        query_id: str = None,
        query_image_path: Optional[str] = None,
        create_collage: bool = True
    ) -> List[Dict]:
        """
        Save decrypted images using image_id from metadata.
        
        Args:
            decrypted_images: List of (image_bytes, metadata) tuples
            query_id: Optional query identifier for organizing results
            query_image_path: Path to original query image (for collage)
            create_collage: Whether to create visualization collage
        
        Returns:
            List of saved file information
        """
        
        print(f"\n[ImageSaver] Saving {len(decrypted_images)} images...")
        
        # Create query-specific subdirectory
        if query_id:
            save_dir = self.output_dir / query_id
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_dir = self.output_dir / f"query_{timestamp}"
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        image_paths_for_collage = []
        
        for image_bytes, metadata in decrypted_images:
            try:
                # ✅ UPDATED: Extract image_id from metadata
                image_id = self._extract_image_id(metadata)
                rank = metadata.get('search_rank', 0)
                
                # ✅ NEW: Filename is just image_id (without rank prefix for evaluator)
                # Format: <image_id>.jpg (e.g., cat_042.jpg, dog_115.jpg)
                filename = f"{image_id}.jpg"
                file_path = save_dir / filename
                
                # Save image
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
                
                # Track for collage (with rank info)
                image_paths_for_collage.append((rank, file_path, image_id))
                
                # Save metadata with rank info
                metadata_path = save_dir / f"rank{rank:02d}_{image_id}_metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                saved_info = {
                    'rank': rank,
                    'image_id': image_id,
                    'file_path': str(file_path),
                    'metadata_path': str(metadata_path),
                    'size_bytes': len(image_bytes)
                }
                
                saved_files.append(saved_info)
                
                print(f"[Save] ✓ Rank {rank}: {filename} ({len(image_bytes):,} bytes)")
                
            except Exception as e:
                print(f"[ERROR] Failed to save image {metadata.get('image_id', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save summary
        summary_path = save_dir / "retrieval_summary.json"
        summary = {
            'query_id': query_id or save_dir.name,
            'timestamp': datetime.now().isoformat(),
            'total_images': len(saved_files),
            'output_directory': str(save_dir.absolute()),
            'files': saved_files
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"[ImageSaver] ✓ Saved {len(saved_files)} images to: {save_dir}")
        print(f"[ImageSaver] Summary: {summary_path}")
        
        # Create collage
        if create_collage and query_image_path and image_paths_for_collage:
            try:
                collage_path = self._create_collage(
                    query_image_path=query_image_path,
                    ranked_images=image_paths_for_collage,
                    save_dir=save_dir
                )
                print(f"[ImageSaver] 🎨 Collage created: {collage_path.name}")
            except Exception as e:
                print(f"[ERROR] Failed to create collage: {e}")
                import traceback
                traceback.print_exc()
        
        return saved_files
    
    def _extract_image_id(self, metadata: Dict) -> str:
        """
        Extract image_id from metadata with fallback strategies.
        
        Tries multiple possible locations in the JSON structure.
        
        Args:
            metadata: Metadata dict from search response
        
        Returns:
            image_id string
        """
        # Strategy 1: Direct 'image_id' field
        if 'image_id' in metadata:
            return metadata['image_id']
        
        # Strategy 2: Inside 'metadata' nested dict
        if 'metadata' in metadata and isinstance(metadata['metadata'], dict):
            if 'image_id' in metadata['metadata']:
                return metadata['metadata']['image_id']
        
        # Strategy 3: From 'azure_row_key' (blob name)
        if 'azure_row_key' in metadata:
            # azure_row_key format: user_001/image_id_timestamp
            row_key = metadata['azure_row_key']
            # Extract image_id part
            parts = row_key.split('/')
            if len(parts) > 1:
                blob_name = parts[-1]
                # Remove extension if present
                image_id = blob_name.rsplit('.', 1)[0]
                return image_id
        
        # Strategy 4: From 'blob_name'
        if 'blob_name' in metadata:
            blob_name = metadata['blob_name']
            parts = blob_name.split('/')
            if len(parts) > 1:
                image_id = parts[-1].rsplit('.', 1)[0]
                return image_id
        
        # Strategy 5: Use timestamp as fallback
        timestamp = metadata.get('timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
        return f"image_{timestamp}"
    
    def _create_collage(
        self,
        query_image_path: str,
        ranked_images: List[Tuple[int, Path, str]],  # (rank, path, image_id)
        save_dir: Path,
        thumb_size: int = 256
    ) -> Path:
        """Create a visual collage with query + ranked results."""
        # Sort by rank
        ranked_images = sorted(ranked_images, key=lambda x: x[0])
        
        # Load query image
        query_img = Image.open(query_image_path).convert('RGB')
        
        # Load result images
        result_imgs = []
        for rank, img_path, image_id in ranked_images:
            try:
                img = Image.open(img_path).convert('RGB')
                result_imgs.append((rank, img, image_id))
            except Exception as e:
                print(f"[WARNING] Failed to load {img_path}: {e}")
        
        if not result_imgs:
            raise ValueError("No valid result images to create collage")
        
        # Calculate layout
        num_results = len(result_imgs)
        
        # Query image on left (2x2 grid space)
        query_size = thumb_size * 2
        
        # Results in grid on right
        cols = 2  # 2 columns for results
        rows = (num_results + cols - 1) // cols  # Ceiling division
        
        # Canvas dimensions
        padding = 20
        label_height = 40
        
        canvas_width = query_size + (cols * thumb_size) + (padding * 3)
        canvas_height = max(query_size, rows * thumb_size) + (padding * 2) + label_height
        
        # Create canvas
        canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
        draw = ImageDraw.Draw(canvas)
        
        # Try to load font (fallback to default if not available)
        try:
            font_title = ImageFont.truetype("arial.ttf", 24)
            font_label = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font_title = ImageFont.load_default()
                font_label = ImageFont.load_default()
        
        # Draw query image
        query_x = padding
        query_y = padding + label_height
        
        # Resize query maintaining aspect ratio
        query_thumb = self._resize_maintain_aspect(query_img, query_size, query_size)
        canvas.paste(query_thumb, (query_x, query_y))
        
        # Draw "QUERY" label with border
        self._draw_label_box(
            draw, 
            query_x, 
            padding, 
            query_size, 
            label_height, 
            "QUERY", 
            font_title,
            bg_color='#3498db',
            text_color='white'
        )
        
        # Draw result images in grid
        result_start_x = query_x + query_size + padding
        
        for idx, (rank, img, image_id) in enumerate(result_imgs):
            row = idx // cols
            col = idx % cols
            
            x = result_start_x + (col * thumb_size)
            y = query_y + (row * thumb_size)
            
            # Resize result maintaining aspect ratio
            result_thumb = self._resize_maintain_aspect(img, thumb_size, thumb_size)
            canvas.paste(result_thumb, (x, y))
            
            # Draw rank label with image_id
            rank_text = f"#{rank}: {image_id}"
            
            # Choose color based on rank (green for top, yellow for mid, red for low)
            if rank == 1:
                bg_color = '#27ae60'  # Green
            elif rank <= 3:
                bg_color = '#f39c12'  # Orange
            else:
                bg_color = '#e74c3c'  # Red
            
            self._draw_label_box(
                draw,
                x,
                y - label_height,
                thumb_size,
                label_height,
                rank_text,
                font_label,
                bg_color=bg_color,
                text_color='white'
            )
        
        # Draw title at top
        title_text = f"Similarity Search Results - {len(result_imgs)} matches"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(
            ((canvas_width - title_width) // 2, 5),
            title_text,
            fill='black',
            font=font_title
        )
        
        # Save collage
        collage_path = save_dir / "collage_results.jpg"
        canvas.save(collage_path, quality=95)
        
        return collage_path
    
    def _resize_maintain_aspect(
        self, 
        img: Image.Image, 
        target_width: int, 
        target_height: int
    ) -> Image.Image:
        """Resize image maintaining aspect ratio, add padding if needed."""
        # Calculate aspect ratios
        img_aspect = img.width / img.height
        target_aspect = target_width / target_height
        
        if img_aspect > target_aspect:
            # Image is wider - fit to width
            new_width = target_width
            new_height = int(target_width / img_aspect)
        else:
            # Image is taller - fit to height
            new_height = target_height
            new_width = int(target_height * img_aspect)
        
        # Resize
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create canvas with padding
        canvas = Image.new('RGB', (target_width, target_height), color='lightgray')
        
        # Center the image
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        
        canvas.paste(img_resized, (x_offset, y_offset))
        
        return canvas
    
    def _draw_label_box(
        self,
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        bg_color: str = '#3498db',
        text_color: str = 'white'
    ):
        """Draw a colored box with centered text."""
        # Draw background rectangle
        draw.rectangle(
            [(x, y), (x + width, y + height)],
            fill=bg_color,
            outline='black',
            width=2
        )
        
        # Draw text centered
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2
        
        draw.text((text_x, text_y), text, fill=text_color, font=font)
