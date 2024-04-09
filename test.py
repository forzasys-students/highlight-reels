while True:
    print("Choose an action for the clip (default: goal): \n1. Goal\n2. Shot\n3. Yellow card\n4. Red card\n5. Penalty")
    choice = input("Enter your choice (1/2/3/4/5): ")
    if choice == '1':
        print(1)
    elif choice == '2':
        print(2)
    elif choice == '3':
        print(3)
    elif choice == '4':
        print(4)
    elif choice == '5':
        print(5)
    else:
        print(f"Error resolving input '{choice}'")
        continue
    break