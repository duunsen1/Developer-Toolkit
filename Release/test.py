import argparse

def remove_blank_lines(input_file, output_file):
    """
    移除文件中的空白行并保存到新文件
    :param input_file: 输入文件路径
    :param output_file: 输出文件路径
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f_in:
            # 逐行读取并过滤空白行
            cleaned_lines = [line for line in f_in if line.strip()]
        
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.writelines(cleaned_lines)
            
        print(f"成功处理文件！已保存到: {output_file}")
        
    except FileNotFoundError:
        print(f"错误：输入文件 {input_file} 未找到")
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='移除文件中的空白行')
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    # 设置默认输出路径
    output_path = args.output or f"{args.input}.clean.txt"
    
    remove_blank_lines(args.input, output_path)