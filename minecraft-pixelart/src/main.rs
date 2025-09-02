use image::{ImageBuffer, RgbImage};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::io::Write;
use serde_json::json;
use rayon::prelude::*;
use indicatif::{ProgressBar, ProgressStyle};
use std::env;
use std::sync::{Arc, Mutex};

#[derive(Clone, Debug)]
struct BlockTemplate {
    name: String,
    image: RgbImage,
}

#[derive(Clone, Debug, serde::Serialize)]
struct BlockInfo {
    x: u32,
    y: u32,
    z: u32,
    block: String,
    similarity: f64,
}

// 新增：用于缓存的键结构
#[derive(Clone, Hash, PartialEq, Eq, Debug)]
struct PixelBlockKey {
    pixels: Vec<u8>, // 存储所有像素的RGB值
}

impl PixelBlockKey {
    fn from_image(img: &RgbImage) -> Self {
        let mut pixels = Vec::with_capacity((img.width() * img.height() * 3) as usize);
        for pixel in img.pixels() {
            pixels.extend_from_slice(&pixel.0);
        }
        PixelBlockKey { pixels }
    }
}

// 新增：缓存结果结构
#[derive(Clone, Debug)]
struct CacheResult {
    block_name: String,
    similarity: f64,
}

pub struct MinecraftPixelArt {
    image_path: String,
    blocks_folder: String,
    block_templates: Vec<BlockTemplate>,
    block_size: u32,
    // 新增：匹配结果缓存
    cache: Arc<Mutex<HashMap<PixelBlockKey, CacheResult>>>,
}

impl MinecraftPixelArt {
    pub fn new(image_path: String, blocks_folder: String, block_size: u32) -> Self {
        let mut processor = MinecraftPixelArt {
            image_path,
            blocks_folder,
            block_templates: Vec::new(),
            block_size,
            cache: Arc::new(Mutex::new(HashMap::new())),
        };
        processor.load_block_templates();
        processor
    }

    fn load_block_templates(&mut self) {
        println!("正在加载方块模板...");
        
        if !Path::new(&self.blocks_folder).exists() {
            println!("错误: {} 文件夹不存在", self.blocks_folder);
            return;
        }

        let entries = match fs::read_dir(&self.blocks_folder) {
            Ok(entries) => entries,
            Err(e) => {
                println!("读取文件夹出错: {}", e);
                return;
            }
        };

        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                if let Some(extension) = path.extension() {
                    let ext = extension.to_string_lossy().to_lowercase();
                    if ext == "png" || ext == "jpg" || ext == "jpeg" {
                        match self.load_single_block(&path) {
                            Ok(template) => self.block_templates.push(template),
                            Err(e) => println!("无法加载 {:?}: {}", path, e),
                        }
                    }
                }
            }
        }

        println!("成功加载 {} 个方块模板", self.block_templates.len());
    }

    fn load_single_block(&self, path: &Path) -> Result<BlockTemplate, Box<dyn std::error::Error>> {
        let img = image::open(path)?;
        let resized = img.resize_exact(self.block_size, self.block_size, image::imageops::FilterType::Lanczos3);
        let rgb_img = resized.to_rgb8();
        
        let name = path.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();

        Ok(BlockTemplate {
            name,
            image: rgb_img,
        })
    }

    fn calculate_similarity(&self, img1: &RgbImage, img2: &RgbImage) -> f64 {
        // 只使用MSE (均方误差) 计算相似度
        // MSE值越小表示越相似
        let mut mse = 0.0;
        let mut count = 0;

        for (p1, p2) in img1.pixels().zip(img2.pixels()) {
            let r_diff = p1[0] as f64 - p2[0] as f64;
            let g_diff = p1[1] as f64 - p2[1] as f64;
            let b_diff = p1[2] as f64 - p2[2] as f64;
            
            mse += r_diff * r_diff + g_diff * g_diff + b_diff * b_diff;
            count += 1;
        }

        mse /= count as f64;
        mse
    }

    // 修改：带缓存的方块匹配函数
    fn find_best_matching_block_cached(&self, block_img: &RgbImage) -> Option<(String, f64)> {
        // 生成缓存键
        let cache_key = PixelBlockKey::from_image(block_img);
        
        // 先检查缓存
        {
            let cache = self.cache.lock().unwrap();
            if let Some(cached_result) = cache.get(&cache_key) {
                return Some((cached_result.block_name.clone(), cached_result.similarity));
            }
        }
        
        // 缓存中没有，进行实际匹配
        let result = self.find_best_matching_block(block_img);
        
        // 将结果存入缓存
        if let Some((ref block_name, similarity)) = result {
            let mut cache = self.cache.lock().unwrap();
            cache.insert(cache_key, CacheResult {
                block_name: block_name.clone(),
                similarity,
            });
        }
        
        result
    }

    fn find_best_matching_block(&self, block_img: &RgbImage) -> Option<(String, f64)> {
        let mut best_match: Option<(String, f64)> = None;
        
        for template in &self.block_templates {
            let mse = self.calculate_similarity(block_img, &template.image);
            
            // 如果找到完美匹配(MSE=0)，立即返回
            if mse == 0.0 {
                return Some((template.name.clone(), mse));
            }
            
            // 更新最佳匹配(寻找最小MSE)
            match &best_match {
                None => best_match = Some((template.name.clone(), mse)),
                Some((_, best_mse)) => {
                    if mse < *best_mse {
                        best_match = Some((template.name.clone(), mse));
                    }
                }
            }
        }
        
        best_match
    }

    pub fn process_image(&self) -> Result<Vec<BlockInfo>, Box<dyn std::error::Error>> {
        println!("正在加载主图片...");
        
        let main_img = image::open(&self.image_path)?;
        let rgb_img = main_img.to_rgb8();
        
        println!("图片尺寸: {}x{}", rgb_img.width(), rgb_img.height());

        let grid_width = rgb_img.width() / self.block_size;
        let grid_height = rgb_img.height() / self.block_size;
        
        println!("网格尺寸: {} x {}", grid_width, grid_height);

        let total_blocks = (grid_width * grid_height) as usize;
        let pb = ProgressBar::new(total_blocks as u64);
        pb.set_style(ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta}) 缓存命中: {msg}")
            .unwrap()
            .progress_chars("#>-"));

        // 用于统计缓存命中率
        let cache_hits = Arc::new(Mutex::new(0u32));
        let total_processed = Arc::new(Mutex::new(0u32));

        // 并行处理每个方块
        let block_mapping: Vec<BlockInfo> = (0..grid_height)
            .into_par_iter()
            .flat_map(|y| {
                let rgb_img_clone = rgb_img.clone();
                let pb_clone = pb.clone();
                let cache_hits_clone = cache_hits.clone();
                let total_processed_clone = total_processed.clone();
                
                (0..grid_width).into_par_iter().filter_map(move |x| {
                    let start_x = x * self.block_size;
                    let start_y = y * self.block_size;
                    let rgb_img = rgb_img_clone.clone();
                    let pb = pb_clone.clone();
                    
                    // 提取16x16的方块
                    let mut block_img = ImageBuffer::new(self.block_size, self.block_size);
                    for (block_x, block_y, pixel) in block_img.enumerate_pixels_mut() {
                        let img_x = start_x + block_x;
                        let img_y = start_y + block_y;
                        if img_x < rgb_img.width() && img_y < rgb_img.height() {
                            *pixel = *rgb_img.get_pixel(img_x, img_y);
                        }
                    }

                    // 检查缓存前的大小
                    let cache_size_before = {
                        let cache = self.cache.lock().unwrap();
                        cache.len()
                    };

                    // 使用带缓存的匹配函数
                    let result = self.find_best_matching_block_cached(&block_img);

                    // 检查是否是缓存命中
                    let cache_size_after = {
                        let cache = self.cache.lock().unwrap();
                        cache.len()
                    };
                    
                    if cache_size_after == cache_size_before {
                        // 缓存命中
                        let mut hits = cache_hits_clone.lock().unwrap();
                        *hits += 1;
                    }
                    
                    let mut total = total_processed_clone.lock().unwrap();
                    *total += 1;
                    
                    // 更新进度条显示缓存命中率
                    let hits = *cache_hits_clone.lock().unwrap();
                    let total_count = *total;
                    let hit_rate = if total_count > 0 { (hits as f64 / total_count as f64 * 100.0) } else { 0.0 };
                    pb.set_message(format!("{:.1}%", hit_rate));

                    if let Some((best_block, similarity)) = result {
                        pb.inc(1);
                        Some(BlockInfo {
                            x,
                            y,
                            z: 0,
                            block: best_block,
                            similarity,
                        })
                    } else {
                        pb.inc(1);
                        None
                    }
                })
            })
            .collect();

        // 显示最终的缓存统计
        let final_hits = *cache_hits.lock().unwrap();
        let final_total = *total_processed.lock().unwrap();
        let final_hit_rate = if final_total > 0 { (final_hits as f64 / final_total as f64 * 100.0) } else { 0.0 };
        
        pb.finish_with_message(format!("处理完成! 缓存命中率: {:.1}%", final_hit_rate));
        
        println!("缓存统计:");
        println!("- 总处理方块数: {}", final_total);
        println!("- 缓存命中次数: {}", final_hits);
        println!("- 缓存命中率: {:.1}%", final_hit_rate);
        println!("- 唯一方块模式数: {}", self.cache.lock().unwrap().len());
        
        Ok(block_mapping)
    }

    pub fn generate_mcfunction(&self, block_mapping: &[BlockInfo], output_file: &str) -> Result<(), Box<dyn std::error::Error>> {
        println!("正在生成 {}...", output_file);
        
        let mut file = fs::File::create(output_file)?;
        
        writeln!(file, "# Minecraft像素画生成函数")?;
        writeln!(file, "# 自动生成 - 请在游戏中执行\n")?;
        
        for block_info in block_mapping {
            let command = format!(
                "setblock ~{} ~{} ~{} minecraft:{}\n",
                block_info.x, block_info.z, block_info.y, block_info.block
            );
            file.write_all(command.as_bytes())?;
        }
        
        println!("成功生成 {} 个方块命令", block_mapping.len());
        Ok(())
    }

    pub fn generate_summary(&self, block_mapping: &[BlockInfo], output_file: &str) -> Result<(), Box<dyn std::error::Error>> {
        let mut block_count: HashMap<String, u32> = HashMap::new();
        let mut total_similarity = 0.0;

        for block_info in block_mapping {
            *block_count.entry(block_info.block.clone()).or_insert(0) += 1;
            total_similarity += block_info.similarity;
        }

        let average_similarity = total_similarity / block_mapping.len() as f64;
        
        // 按使用次数排序
        let mut sorted_blocks: Vec<_> = block_count.into_iter().collect();
        sorted_blocks.sort_by(|a, b| b.1.cmp(&a.1));
        
        // 添加缓存统计信息
        let cache_size = self.cache.lock().unwrap().len();
        
        let summary = json!({
            "total_blocks": block_mapping.len(),
            "unique_blocks": sorted_blocks.len(),
            "unique_pixel_patterns": cache_size,
            "block_count": sorted_blocks.into_iter().collect::<HashMap<_, _>>(),
            "average_similarity": average_similarity
        });

        let mut file = fs::File::create(output_file)?;
        file.write_all(serde_json::to_string_pretty(&summary)?.as_bytes())?;

        println!("处理摘要已保存到 {}", output_file);
        println!("总方块数: {}", block_mapping.len());
        println!("使用的不同方块类型: {}", summary["unique_blocks"]);
        println!("唯一像素模式数: {}", cache_size);
        println!("平均相似度: {:.2}", average_similarity);

        Ok(())
    }
}

fn print_usage() {
    println!("用法: minecraft-pixelart [选项]");
    println!();
    println!("选项:");
    println!("  -i, --image <路径>       输入图片路径 (默认: input_image.png)");
    println!("  -b, --blocks <路径>      方块模板文件夹路径 (默认: ./block)");
    println!("  -s, --size <数字>        方块大小 (默认: 16)");
    println!("  -o, --output <名称>      输出文件名前缀 (默认: minecraft_pixelart)");
    println!("  -h, --help               显示帮助信息");
    println!();
    println!("示例:");
    println!("  minecraft-pixelart");
    println!("  minecraft-pixelart -i my_image.png -b ./my_blocks -s 32 -o my_pixelart");
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    
    // 默认值
    let mut image_path = "input_image.png".to_string();
    let mut blocks_folder = "./block".to_string();
    let mut block_size = 16u32;
    let mut output_name = "minecraft_pixelart".to_string();
    
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "-h" | "--help" => {
                print_usage();
                return Ok(());
            }
            "-i" | "--image" => {
                if i + 1 < args.len() {
                    image_path = args[i + 1].clone();
                    i += 2;
                } else {
                    println!("错误: -i/--image 参数需要一个值");
                    print_usage();
                    return Ok(());
                }
            }
            "-b" | "--blocks" => {
                if i + 1 < args.len() {
                    blocks_folder = args[i + 1].clone();
                    i += 2;
                } else {
                    println!("错误: -b/--blocks 参数需要一个值");
                    print_usage();
                    return Ok(());
                }
            }
            "-s" | "--size" => {
                if i + 1 < args.len() {
                    match args[i + 1].parse::<u32>() {
                        Ok(size) => {
                            block_size = size;
                            i += 2;
                        }
                        Err(_) => {
                            println!("错误: -s/--size 参数需要一个值");
                            print_usage();
                            return Ok(());
                        }
                    }
                } else {
                    println!("错误: -s/--size 参数需要一个值");
                    print_usage();
                    return Ok(());
                }
            }
            "-o" | "--output" => {
                if i + 1 < args.len() {
                    output_name = args[i + 1].clone();
                    i += 2;
                } else {
                    println!("错误: -o/--output 参数需要一个值");
                    print_usage();
                    return Ok(());
                }
            }
            _ => {
                println!("未知参数: {}", args[i]);
                print_usage();
                return Ok(());
            }
        }
    }

    println!("开始处理Minecraft像素画...");
    println!("输入图片: {}", image_path);
    println!("方块模板文件夹: {}", blocks_folder);
    println!("方块大小: {}", block_size);
    
    let processor = MinecraftPixelArt::new(image_path, blocks_folder, block_size);
    
    if processor.block_templates.is_empty() {
        println!("错误: 没有找到任何方块模板，请检查 {} 文件夹", processor.blocks_folder);
        return Ok(());
    }

match processor.process_image() {
        Ok(block_mapping) => {
            let mcfunction_file = format!("{}.mcfunction", output_name);
            let summary_file = format!("{}_summary.json", output_name);
            
            processor.generate_mcfunction(&block_mapping, &mcfunction_file)?;
            processor.generate_summary(&block_mapping, &summary_file)?;
            
            println!("\n处理完成！");
            println!("生成的文件:");
            println!("- {} (Minecraft命令文件)", mcfunction_file);
            println!("- {} (处理摘要)", summary_file);
        }
        Err(e) => {
            println!("处理失败: {}", e);
        }
    }

    Ok(())
}
